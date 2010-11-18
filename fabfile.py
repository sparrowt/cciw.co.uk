from collections import namedtuple
from datetime import datetime
from fabric.api import run, local, abort, env, put
from fabric.contrib import files
from fabric.decorators import hosts, runs_once
from fabric.context_managers import cd, settings
import os

#  fabfile for deploying CCIW
#
# == Overview ==
#
# There are two targets, STAGING and PRODUCTION.
# They are almost identical, with these differences
# - STAGING is on staging.cciw.co.uk
# - PRODUCTION is on www.cciw.co.uk
# - They have different databases
# - They have different apps on the webfaction server
#    - for the django project app
#    - for the static app
#    - for the usermedia app
# - STAGING has SSL turned off.
#
# settings_priv.py and settings.py controls these things.
#
# In each target, we aim for atomic switching from one version to the next.
# This is not quite possible, but as much as possible the different versions
# are kept separate, preparing the new one completely before switching to it.
#
# To achieve this, new code is uploaded to a new 'dest_dir' which is timestamped,
# inside the 'src' dir in the cciw app directory.

# /home/cciw/webapps/cciw/         # PRODUCTION or
# /home/cciw/webapps/cciw_staging/ # STAGING
#    src/
#       src-2010-10-11_07-20-34/
#          env/                    # virtualenv dir
#          project/                # uploaded from local
#          deps/
#            django/
#            django-mailer/
#          static/                 # built once uploaded

# At the same level as 'srf-2010-10-11_07-20-34', there is a 'current' symlink
# which points to the most recent one. The apache instance looks at this (and
# the virtualenv dir inside it) to run the app.

# There is a webfaction app that points to src/current/static for serving static
# media. (One for production, one for staging). There is also a 'cciw_usermedia'
# app which is currently shared between production and staging. (This will only
# be a problem if usermedia needs to be re-organised).

# For speed, a new src-XXX dir is created by copying the 'current' one, and then
# using rsync and other updates. This is much faster than transferring
# everything and also rebuilding the virtualenv from scratch.

# When deploying, once the new directory is ready, the apache instance is
# stopped, the database is upgraded, and the 'current' symlink is switched. Then
# the apache instance is started.

# The information about this layout is unfortunately spread around a couple of
# places - this file and the settings file - because it is needed in both at
# different times.


env.hosts = ["cciw@cciw.co.uk"]

Target = namedtuple('Target', 'django_app dbname')

STAGING = Target(
    django_app = "cciw_staging",
    dbname = "cciw_staging",
)
PRODUCTION = Target(
    django_app = "cciw",
    dbname = "cciw",
)

this_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(this_dir)
webapps_root = '/home/cciw/webapps'

# The path (relative to parent_dir) to where the project source code is stored:
project_dir = 'project'
# The relative path to where the dependencies source code is stored (for those
# not installed using pip)
deps_dir = 'deps'


def _get_subdirs(dirname):
    return [f for f in os.listdir(dirname)
            if os.path.isdir(os.path.join(dirname, f))]

deps = _get_subdirs(parent_dir + "/" + deps_dir)


@runs_once
def ensure_dependencies():
    hg_branch = local("cd deps/django; hg branch")
    if hg_branch.strip() != 'default':
        abort("Django src on incorrect branch")


def test():
    ensure_dependencies()
    local("cd project; ./manage.py test cciwmain officers tagging utils --settings=cciw.settings_tests", capture=False)


def _prepare_deploy():
    ensure_dependencies()
    # test that we can do forwards and backwards migrations?
    # check that there are no outstanding changes.


@hosts("cciw@cciw.co.uk")
def backup_database(target, label):
    fname = "%s-%s.db" % (target.dbname, label)
    run("dump_cciw_db.sh %s %s" % (target.dbname, fname))


def run_venv(command):
    run("source %s/bin/activate" % env.venv + " && " + command)


def virtualenv(venv_dir):
    """
    Context manager that established a virtualenv to use,
    """
    return settings(venv=venv_dir)


def _update_symlink(dest_dir):
    with cd(dest_dir + "/../"):
        if files.exists("current"):
            run("rm current")
        run("ln -s %s current" % os.path.basename(dest_dir))


def _fix_ipython():
    # Fix up IPython, which gets borked by the re-installation of the virtualenv
    with settings(warn_only=True):
        run_venv("pip uninstall -y ipython")
        run_venv("pip install ipython")


def _update_virtualenv(dest_dir, additional_sys_paths):
    # Update virtualenv in new dir.
    with cd(dest_dir):
        # We should already have a virtualenv, but it will need paths updating
        run("virtualenv --python=python2.5 env")
        # Need this to stop ~/lib/ dirs getting in:
        run("touch env/lib/python2.5/sitecustomize.py")
        with virtualenv(dest_dir + "/env"):
            with cd("project"):
                run_venv("pip install -r requirements.txt")
            _fix_ipython()

        # Need to add project and deps to path.
        # Could do 'python setup.py develop' but not all projects support it
        pth_file = '\n'.join("../../../../" + n for n in additional_sys_paths)
        pth_name = "deps.pth"
        with open(pth_name, "w") as fd:
            fd.write(pth_file)
        put(pth_name, dest_dir + "/env/lib/python2.5/site-packages")
        os.unlink(pth_name)


def _stop_apache(target):
    run (webapps_root + "/" + target.django_app + "/apache2/bin/stop")


def _start_apache(target):
    run (webapps_root + "/" + target.django_app + "/apache2/bin/start")


def _restart_apache(target):
    with settings(warn_only=True):
        _stop_apache(target)
    _start_apache(target)


def rsync_dir(local_dir, dest_dir):
    # clean first
    with settings(warn_only=True):
        local("find %s -name '*.pyc' -exec 'rm {}' ';'" % local_dir)
    local("rsync -r -L --delete --exclude='_build' --exclude='.hg' --exclude='.git' --exclude='.svn' --delete-excluded %s cciw@cciw.co.uk:%s/" % (local_dir, dest_dir), capture=False)


def _copy_local_sources(dest_dir):
    # Upload local sources. For speed, we:
    # - make a copy of the sources that are there already, if they exist.
    # - rsync to the copies.
    # This also copies the virtualenv which is contained in the same folder,
    # which saves a lot of time with installing.

    current_srcs = os.path.dirname(dest_dir) + "/current"

    if files.exists(current_srcs):
        run("cp -a -L %s %s" % (current_srcs, dest_dir))
    else:
        run("mkdir %s" % dest_dir)

    with cd(parent_dir):
        # rsync the project.
        rsync_dir(project_dir, dest_dir)
        # rsync the deps
        rsync_dir(deps_dir, dest_dir)


def _copy_protected_downloads():
    # We currently don't need this to be separate for staging and production
    rsync_dir(os.path.join(parent_dir, "resources/protected_downloads"),
              os.path.join(webapps_root, 'cciw_protected_downloads_src'))


def _build_static(dest_dir):
    # This always copies all files anyway, and we want to delete any unwanted
    # files, so we start from clean dir.
    with cd(dest_dir):
        run("rm -rf static/")

    with virtualenv(dest_dir + "/env"):
        with cd(dest_dir + "/" + project_dir):
            run_venv("./manage.py collectstatic --settings=cciw.settings --noinput")

    with cd(dest_dir):
        run("chmod -R ugo+r static")

def _deploy(target):
    label = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
    _prepare_deploy()
    db_backup_name = backup_database(target, label)

    dest_dirname = "src-%s" % label
    dest_dir = webapps_root + "/" + target.django_app + "/src/" + dest_dirname

    additional_sys_paths = [deps_dir + "/" + d for d in deps] + [project_dir]

    _copy_local_sources(dest_dir)
    _copy_protected_downloads()
    _update_virtualenv(dest_dir, additional_sys_paths)

    _build_static(dest_dir)

    _stop_apache(target)

    # TODO
    # - do db migrations
    # - if unsuccessful
    #    - rollback db migrations
    #      - if unsuccessful, restore from db_backup_name
    # - if successful
    #    - remove 'current' symlink (OK if not present)
    #    - add new current symlink to '$datetime' dir
    #  - start apache

    _update_symlink(dest_dir)
    _start_apache(target)


def deploy_staging():
    _deploy(STAGING)


def deploy_production():
    _deploy(PRODUCTION)
