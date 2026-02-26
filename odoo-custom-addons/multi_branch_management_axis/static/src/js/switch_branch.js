odoo.define('multi_branch_management_axis.SwitchBranchMenu', function(require) {
"use strict";

/**
 * When Odoo is configured in multi-company mode, users should obviously be able
 * to switch their interface from one company to the other.  This is the purpose
 * of this widget, by displaying a dropdown menu in the systray.
 */

var config = require('web.config');
var core = require('web.core');
var session = require('web.session');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');
var utils = require('web.utils');

var _t = core._t;

var rpc = require('web.rpc');


 var branchID = [];
console.log("my branmch :..:", branchID)

var SwitchBranchMenu = Widget.extend({
    template: 'SwitchBranchMenu',
    events: {
        'click .dropdown-item[data-menu] div.log_into_branch': '_onSwitchBranchClick',
        'keydown .dropdown-item[data-menu] div.log_into_branch': '_onSwitchBranchClick',
        'click .dropdown-item[data-menu] div.toggle_branch': '_onToggleBranchClick',
        'keydown .dropdown-item[data-menu] div.toggle_branch': '_onToggleBranchClick',
    },
    /**
     * @override
     */
    init: function () {
        
        this._super.apply(this, arguments);
        this.isMobile = config.device.isMobile;
        this._onSwitchBranchClick = _.debounce(this._onSwitchBranchClick, 1500, true);
        if(session.user_branches.current_branch){
            utils.set_cookie('bids', session.user_branches.current_branch[0] );
            $.bbq.pushState({'bids': session.user_branches.current_branch[0]  }, 0);
        }
    },

    /**
     * @override
     */
    willStart: function () {
        var self = this;
        var state = $.bbq.getState();
        var current_branch_id = session.user_branches.current_branch[0]
        if (!state.bids) {
            state.bids = utils.get_cookie('bids')  ? utils.get_cookie('bids') : String(current_branch_id);
        }
        var statebranch_IDS = _.map(state.bids.split(','), function (bid) { 
            return parseInt(bid)
        });
        var statebranchIDS = []
        for(var i = 0; i < statebranch_IDS.length; i++){
            if(statebranch_IDS[i]){
                statebranchIDS.push(statebranch_IDS[i])
            }
        }
        var userbranchIDS = _.map(session.user_branches.allowed_branches, function(branch) {
            return branch[0]
        });


        session.user_context.allowed_branch_ids = statebranchIDS;
        $.bbq.pushState(state);
       this.allowed_branch_ids = String(session.user_context.allowed_branch_ids)
                                   .split(',')
                                   .map(function (id) {return parseInt(id);});

       this.user_branches = session.user_branches.allowed_branches;
       if (this.allowed_branch_ids[1]){
          this.current_branch = this.allowed_branch_ids[1];
       }else{
          this.current_branch = this.allowed_branch_ids[0];
       }
       if (self.current_branch && self.current_branch != NaN){
           this.current_branch_name = _.find(session.user_branches.allowed_branches, function (branch) {
               return branch[0] === self.current_branch;
           });
           if(this.current_branch_name){
                this.current_branch_name = this.current_branch_name[1]
           }
           return this._super.apply(this, arguments);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent|KeyEvent} ev
     */

    _onSwitchBranchClick: function (ev) {
        var self = this;
         console.log('start : _onSwitchBranchClick click', this );
        if (ev.type == 'keydown' && ev.which != $.ui.keyCode.ENTER && ev.which != $.ui.keyCode.SPACE) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        var dropdownItem = $(ev.currentTarget).parent();
        var dropdownMenu = dropdownItem.parent();

        var companyID = dropdownItem.data('branch-id');
         branchID.pop();
        branchID.push(companyID);
//        var vals = {};
//        vals['branch_id'] = parseInt(companyID);
//        console.log("vals:", vals)

         var user_branch = this._rpc({
            model: 'res.users',
            method: 'res_user_branch',
             args: [[session.uid]],
             kwargs:  { 'branch':branchID, 'user':session.uid},
        });


        var branch_name = dropdownItem.data('branch-name');        
        var allowed_branch_ids = this.allowed_branch_ids;

        console.log("allowed_branch_ids:111:", allowed_branch_ids)
        if (dropdownItem.find('.fa-square-o').length) {
            // 1 enabled company: Stay in single company mode
            if (this.allowed_branch_ids.length === 1) {
                if (this.isMobile) {
                    dropdownMenu = dropdownMenu.parent();
                }
                dropdownMenu.find('.fa-check-square').removeClass('fa-check-square').addClass('fa-square-o');
                dropdownItem.find('.fa-square-o').removeClass('fa-square-o').addClass('fa-check-square');
                allowed_branch_ids = [(companyID, branch_name)];
            } else { // Multi company mode
                allowed_branch_ids.push([(companyID, branch_name)]);
                dropdownItem.find('.fa-square-o').removeClass('fa-square-o').addClass('fa-check-square');
            }
        }
        $(ev.currentTarget).attr('aria-pressed', 'true');
        var hash = $.bbq.getState()

        // hash.bids = session.user_branches.allowed_branches.sort(function(a, b) {
        //     console.log(">>>>>>>>.. a, b, co ", a,b,companyID )
        //     if (a === companyID) {
        //         return -1;
        //     } else if (b === companyID) {
        //         return 1;
        //     } else {
        //         return a - b;
        //     }
        // }).join(',');
        hash.bids = String(companyID)
        utils.set_cookie('bids', hash.bids || String(companyID));
        $.bbq.pushState({'bids': hash.bids}, 0);
        location.reload();




    },



    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent|KeyEvent} ev
     */
    _onToggleBranchClick: function (ev) {
        console.log('Ttogglr brancch click:', ev);
        if (ev.type == 'keydown' && ev.which != $.ui.keyCode.ENTER && ev.which != $.ui.keyCode.SPACE) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        var dropdownItem = $(ev.currentTarget).parent();
        var companyID = dropdownItem.data('branch-id');
        branchID.push(companyID);
        var allowed_branch_ids = this.allowed_branch_ids;
        
        var current_company_id = allowed_branch_ids[0];
        if (dropdownItem.find('.fa-square-o').length) {
            allowed_branch_ids.push(companyID);
            dropdownItem.find('.fa-square-o').removeClass('fa-square-o').addClass('fa-check-square');
            $(ev.currentTarget).attr('aria-checked', 'true');
        } else {
            allowed_branch_ids.splice(allowed_branch_ids.indexOf(companyID), 1);
            dropdownItem.find('.fa-check-square').addClass('fa-square-o').removeClass('fa-check-square');
            $(ev.currentTarget).attr('aria-checked', 'false');
        }
        // session.setCompanies(current_company_id, allowed_branch_ids);
        var hash = $.bbq.getState()

        var add = false
        var list = ''
        if (hash.bids){
            for (var i=0; i <= hash.bids.length; i++){
                if (hash.bids[i] && hash.bids[i] != companyID && hash.bids[i] != ',' ){
                    if(list.length == 0){

                     list =  hash.bids[i]
                    }
                    else{
                        list = list + ',' + hash.bids[i]
                    }
                }
            }
            for (var i=0; i <= hash.bids.length; i++){
                if (hash.bids[i] && hash.bids[i] == companyID ){
                    add = true
                }
            }
        }
        if (add){
            hash.bids = list
        }
        else{
            hash.bids =  hash.bids +',' + String(companyID)
        }
        utils.set_cookie('bids', hash.bids || String(companyID));
        console.log("----compan brachL...:", companyID)
        $.bbq.pushState({'bids': hash.bids}, 0);
        location.reload();

        var user_branches = this._rpc({
            model: 'res.users',
            method: 'res_user_branch_clcik',
             args: [[session.uid]],
             kwargs:  { 'branch':allowed_branch_ids, 'user':session.uid},
        });
//         location.reload();
    },

});

if (session.display_switch_company_menu) {
    SystrayMenu.Items.push(SwitchBranchMenu);
}

return SwitchBranchMenu;

});
