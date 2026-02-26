odoo.define('pos_extend.CashBoxPopup', function (require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');

    const { useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');

    class CashBoxPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.symbol = this.env.pos.currency.symbol;
            this.inputRef = useRef('input')
            this.amount_list = ['0.05','0.10','0.20','0.50','1.00','2.00','5.00','10.00','20.00','50.00','100.00']
        }
        mounted() {
            // var txt_cbv = document.querySelectorAll('#txt_cbv')
            // var amount_list = amount_list = ['0.10','0.20','0.50','1.00','2.00','5.00','10.00','20.00','50.00','100.00']
            // var ind = 0
            // txt_cbv.forEach(function(el){
            //     console.log('ind ---',ind)
            //     el.value = amount_list[ind]
            //     ind += 1
            // })
        }
        _input_txt(e){
            e.target.value = e.target.value.replace(/[^0-9.]/g, '').replace(/(\..*?)\..*/g, '$1')
        }
        _keyup_txt_cb(e){
            var value = e.target.value
            
            var coin_bill_value = e.target.closest('tr').querySelector('[name=coin_bill_value]')
            var cb_subtotal = e.target.closest('tr').querySelector('[name=cb_subtotal]')

            var total = parseFloat(value) * parseFloat(coin_bill_value.value)
            cb_subtotal.value = total ? total.toFixed(2) : '0.00'

            var txt_subtotal = document.querySelectorAll('#txt_subtotal')
            var total = 0.00
            txt_subtotal.forEach(function(el){
                if (parseFloat(el.value) > 0){
                    total += parseFloat(el.value)
                }
            })
            $("#total").html(total.toFixed(2))
        }
        _keyup_txt_cbv(e){
            var value = e.target.value

            var coin_bill = e.target.closest('tr').querySelector('[name=coin_bill]')
            var cb_subtotal = e.target.closest('tr').querySelector('[name=cb_subtotal]')

            var total = parseFloat(value) * parseFloat(coin_bill.value)
            cb_subtotal.value = total ? total.toFixed(2) : '0.00'
            
            var txt_subtotal = document.querySelectorAll('#txt_subtotal')
            var total = 0.00
            txt_subtotal.forEach(function(el){
                if (parseFloat(el.value) > 0){
                    total += parseFloat(el.value)
                }
            })
            $("#total").html(total.toFixed(2))

        }
        _total_subtotal(){
            var txt_subtotal = document.querySelectorAll('#txt_subtotal')
            var total = 0.00
            txt_subtotal.forEach(function(el){
                if (parseFloat(el.value) > 0){
                    total += parseFloat(el.value)
                }
            })
            $("#total").html(total.toFixed(2))
            return total
        }
        _add_item(e){

            var clonedRow = $('tbody tr:first').clone();
            clonedRow.find('input').val('');
            clonedRow.find('[name="coin_bill"]').on('input',this._input_txt)
            clonedRow.find('[name="coin_bill_value"]').on('input',this._input_txt)
            
            clonedRow.find('[name="coin_bill"]').on('keyup',this._keyup_txt_cb)
            clonedRow.find('[name="coin_bill_value"]').on('keyup',this._keyup_txt_cbv)
            
            clonedRow.find('[id="delete_item"]').on('click',this._delete_item)

            $('#tr_add_item').before(clonedRow)
        }
        _delete_item(e){
            var cb_subtotal = e.target.closest('tr').querySelector('[name=cb_subtotal]')

            if (cb_subtotal.value > 0){
                var total = parseFloat($("#total").html()) - parseFloat(cb_subtotal.value)
                $("#total").html(total.toFixed(2))
            }

            e.target.closest('tr').remove()            
        }
        getPayload() {
            var total = this._total_subtotal();
            var cashbox_input = $(".cashbox-input");
            cashbox_input.val(total.toFixed(2));

            // Print the cashbox popup details
            console.log('CashBoxPopup Details:');
            console.log('Total Amount:', total.toFixed(2));

            return {'cashOpeningTotal':total.toFixed(2)};
        }
		

        print_report() {
			
			const posName = this.env.pos.config.name;
			const cashier = this.env.pos.get_cashier();	
   


		   const printWindow = window.open('', '_blank');
			printWindow.document.write('<html><head><title>CashBoxPopup Report</title>');
			printWindow.document.write('<style>table { width: 100%; } th, td { text-align: center; padding: 5px; }</style>');
			printWindow.document.write('</head><body>');

			// Set the paper format page width to 70
			printWindow.document.write('<style>@page { size: 70mm; }</style>');


			
 

            // Print the cashbox popup report
			  printWindow.document.write('<h2 style="text-align: center;">Opening Balance</h2>');
			  printWindow.document.write('<p style="font-size: 10px;">Date: ' + formatDate(new Date()) + '</p>');
			  printWindow.document.write('<p style="font-size: 10px;">POS: ' + posName + '</p>');
			  printWindow.document.write('<p style="font-size: 10px;">Cashier: ' + cashier.name + '</p>');
			  printWindow.document.write('<p>Total Amount: ' + this._total_subtotal().toFixed(2) + '</p>');
            // Add more content or customize the report layout as needed

            printWindow.document.write('</body></html>');
            printWindow.document.close();

            // Wait for the window to load and then trigger printing
            printWindow.onload = function() {
                printWindow.print();
                printWindow.close();
            };
			function formatDate(date) {
			  var day = date.getDate();
			  var month = date.getMonth() + 1;
			  var year = date.getFullYear().toString().slice(-2);

			  day = day < 10 ? '0' + day : day;
			  month = month < 10 ? '0' + month : month;

			  return day + '/' + month + '/' + year;
			}			  
        }	
    }
    CashBoxPopup.template = 'CashBoxPopup';

    CashBoxPopup.defaultProps = {
        confirmText: 'Confirm',
        cancelText: 'Cancel',
        title: '',
        body: '',
    };

    Registries.Component.add(CashBoxPopup);

    return CashBoxPopup;
});
