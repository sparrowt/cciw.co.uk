(function($){

    // Global that is true if a row of officer details is in 'edit mode'
    var editOfficerMode = false;

    // Global that is true if the 'add officer' block is visible
    var showAddOfficerBlock = true;


    var refreshLists = function(areas) {
        // Refresh different areas of the page:
        if (areas == null) {
            areas = ["chosen", "available", "noapplication"];
        }
        $.ajax({
            type: "GET",
            url: "?sections=1&" + Math.random().toString(),
            dataType: 'json',
            success: function(data) {
                if (areas.indexOf("chosen") != -1)
                    refreshChosenList(data.chosen);
                if (areas.indexOf("available") != -1)
                    refreshAvailableList(data.available);
                if (areas.indexOf("noapplication") != -1)
                    refreshNoApplicationFormList(data.noapplicationform);
            }
        });
    };

    var addTableSorter = function(sortList) {
        if (sortList == undefined) {
            sortList = [[0,0]];
        }
        $("#id_officer_list_table table").tablesorter({headers:
                                                        { 4: { sorter: false }},
                                                       sortList: sortList
                                                      });
    }


    var refreshChosenList = function(text) {
        var savedSortOrder = $("#id_officer_list_table table").data('tablesorter').sortList;
        $("#id_officer_list_table").children().remove();
        $("#id_officer_list_table").html(text);
        editOfficerMode = false;
        addOfficerListHandlers();
        addTableSorter(savedSortOrder);
    };

    var refreshAvailableList = function(text) {
        var selectedIdx = document.getElementById("id_available_officers").selectedIndex;
        $("#id_available_officers").html(text);
        // restore filter
        $("#id_available_officers_filter").trigger('refresh');
        // restore selected item
        var s = document.getElementById("id_available_officers");
        s.selectedIndex = Math.min(selectedIdx, s.options.length - 1);
    };

    var refreshNoApplicationFormList = function(text) {
        $("#id_noapplicationform").html(text);
    };


    var escape = function(t) {
                     return t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&apos;");
                 };

    var addOfficerListHandlers = function() {
        // event handlers for all 'edit' buttons
        $(".editbtn").click(function(ev) {
            ev.preventDefault();
            if (editOfficerMode) {
                alert("Please finish editing the other row first");
                return;
            }
            editOfficerMode = true;
            var officerId = parseFloat(ev.target.id.substring(8), 10);
            var row = $('#id_officer_table_tr_' + officerId.toString());
            var firstNameCell = row.find('td:nth-child(1)');
            var lastNameCell  = row.find('td:nth-child(2)');
            var emailCell     = row.find('td:nth-child(3)');
            var notesCell     = row.find('td:nth-child(4)');
            var editCell      = row.find('td:nth-child(5)');
            var officer = { firstName: firstNameCell.text(),
                            lastName:  lastNameCell.text(),
                            email:     emailCell.text(),
                            notes:     notesCell.text()
                          };
            // Make input boxes, and save/cancel buttons
            firstNameCell.html('<input size=8 id="id_officer_first_name" type="text" value="' + escape(officer.firstName) + '" /></td>');
            lastNameCell.html('<input size=8 id="id_officer_last_name" type="text" value="' +  escape(officer.lastName) + '" />');
            emailCell.html('<input size=25 id="id_officer_email" type="text" value="' + escape(officer.email) + '" />');
            notesCell.html('<input size=25 id="id_officer_notes" type="text" value="' + escape(officer.notes) + '" />');
            editCell.find('img').hide();
            editCell.append(
                     '<span><a href="#" id="id_officer_save">Save</a> / ' +
                     '<a href="#" id="id_officer_cancel">Cancel</a><span>');
            var showAddOfficerBlockSaved = showAddOfficerBlock;
            var restoreAddBlockState = function() {};
            if (showAddOfficerBlock) {
                // Make room for editing
                addOfficerBlockToggle();
                restoreAddBlockState = addOfficerBlockToggle;
            }

            function setOfficerRow(officerData) {
                firstNameCell.html(escape(officer.firstName));
                lastNameCell.html(escape(officer.lastName));
                emailCell.html('<a href="mailto:' + escape(officer.email) + '">' + escape(officer.email) + '</a>')
                notesCell.html(escape(officer.notes));
                editCell.find('img').show();
                editCell.find('span').remove();
                restoreAddBlockState();
                editOfficerMode = false;
            }

            // 'Cancel' handler:
            row.find('#id_officer_cancel').click(function(ev) {
                ev.preventDefault();
                setOfficerRow(officer);
            });
            // 'Save' handler
            row.find('#id_officer_save').click(function(ev) {
                ev.preventDefault();
                officer.firstName = $('#id_officer_first_name').val();
                officer.lastName  = $('#id_officer_last_name').val();
                officer.email     = $('#id_officer_email').val();
                officer.notes     = $('#id_officer_notes').val();
                setOfficerRow(officer);
                $('#id_officer_list_table table').trigger('update');
                // For responsiveness, we update UI before server has
                // saved data.
                $.ajax({
                    type: 'POST',
                    url: cciw.updateOfficerUrl,
                    data: {'officer_id': officerId.toString(),
                           'first_name': officer.firstName,
                           'last_name': officer.lastName,
                           'email': officer.email,
                           'notes': officer.notes,
                           'camp_id': cciw.campId.toString()
                           },
                    dataType: 'json',
                    success: function() {
                        refreshLists("noapplication");
                    }
                });
            });
        });

        // event handlers for 'remove' buttons
        $(".removebtn").click(function(ev) {
            var officerId = parseFloat(ev.target.id.substring(10), 10);
            // Remove from list
            $.ajax({
                type: "POST",
                url:  cciw.removeOfficerUrl,
                data: "officer_id=" + officerId.toString(),
                dataType: 'json',
                success: function(ev) { refreshLists(); }
            });
            ev.preventDefault();
        });

        // event handlers for 'email' buttons
        $(".emailbtn").click(function(ev) {
            ev.preventDefault();
            if (confirm("This will reset the officer's password and re-send the initial signup e-mail.  Continue?")) {
                var officerId = parseFloat(ev.target.id.substring(9), 10);
                $.ajax({
                    type: "POST",
                    url: cciw.resendEmailUrl,
                    data: "officer_id=" + officerId.toString(),
                    dataType: 'json'
                });
            }
        });
    };

    var officerAddHandler = function(ev) {
        ev.preventDefault();
        if (ev.type == "keyup") {
            var code = (ev.keyCode ? ev.keyCode : ev.which);
            if (code != 13) { // Enter
                return;
            }
        }
        var officer_ids = [];
        var options = $('#id_available_officers').get(0).options;
        for (var i = 0; i < options.length; i++) {
            if (options[i].selected) {
               officer_ids.push(options[i].value)
            }
        }
        if (officer_ids.length == 0) {
            return;
        }
        $.ajax({
            type: "POST",
            url: cciw.addOfficersUrl,
            data: "officer_ids=" + officer_ids.join(','),
            dataType: 'json',
            success: function(ev) { refreshLists(); }
        });
    };

    var newOfficerHandler = function(ev) {
        var popup = $('#id_add_officer_popup');
        popup.find(".iframe_container").html('<iframe src="' + cciw.createOfficerUrl + '?is_popup=1&camp_id=' + cciw.campId + '" width="780" frameborder="0" height="400">');
        popup.css({
            "position": "fixed",
            "top": ($(window).height()/2 - popup.height()/2).toString() + "px",
            "left": ($(window).width()/2 - popup.width()/2).toString() + "px"
        });
        popup.fadeIn("fast");
        $('#id_popup_background').fadeIn('fast');
        ev.preventDefault();
    };

    var newOfficerClose = function(ev) {
        refreshLists();
        $('#id_add_officer_popup').fadeOut('fast');
        $('#id_popup_background').fadeOut('fast');
        ev.preventDefault();
    };

    var addOfficerBlockToggle = function(ev) {
        if (ev != null) {
            ev.preventDefault();
        }
        showAddOfficerBlock = !showAddOfficerBlock;
        var width = showAddOfficerBlock ? '30em' : '4em';
        $('#id_add_officer_div').css({'width':width, 'margin-left': '-' + width})
        $('#id_officer_list_div').css({'margin-right': width})
        if (showAddOfficerBlock) {
            $('#id_add_officer_div .innerright').show();
            $('#id_hide_add_officer_div').text('(hide)');
        } else {
            $('#id_add_officer_div .innerright').hide();
            $('#id_hide_add_officer_div').text('(show)');
        }
    }

    $(document).ready(function(){
        $("#id_available_officers_filter").multiSelectFilter("#id_available_officers");
        addOfficerListHandlers();
        addTableSorter();
        $("#id_available_officers")
           .dblclick(officerAddHandler)
           .keyup(officerAddHandler);
        $('#id_add_officer_btn').click(officerAddHandler);
        $('#id_new_officer_btn').click(newOfficerHandler);
        $('#id_popup_close_btn').click(newOfficerClose);
        $('#id_hide_add_officer_div').click(addOfficerBlockToggle);

        $("#loading").ajaxStart(function(){
            $(this).show();
        });
        $("#loading").ajaxStop(function(){
            $(this).hide();
        });
    });
})(jQuery);