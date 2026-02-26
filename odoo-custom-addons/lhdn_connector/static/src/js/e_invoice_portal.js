/** @odoo-module **/
import { useService, useAutofocus } from "@web/core/utils/hooks";
import { jsonrpc } from "@web/core/network/rpc_service";
import { browser } from "@web/core/browser/browser";

// Variable to store selected files
let selectedFiles = [];



$(document).ready(function() {
        // Attach click event to dynamically created buttons
        $(document).on('click', '.get_lhdn_documents_status', function() {
            var invoiceId = $(this).data('id');
            jsonrpc('/account_move/get_lhdn_documents_status',{
                invoice_id: invoiceId
            }).then(function(response) {
                if (response.success) {
                    browser.location.reload();
//                    Dialog.alert(this, response.message, {
//                        title: 'Success',
//                        type: 'success'
//                    });
                } else {
                console.log("Hiieas errors")
//                    Dialog.alert(this, response.message, {
//                        title: 'Error',
//                        type: 'danger'
//                    });
                }
            })
        });

        $(document).on('click', '.submit_invoice_ins_peppol_network', function() {
            var invoiceId = $(this).data('id');
            jsonrpc('/account_move/manually_documents_send_in_peppol_network',{
                invoice_id: invoiceId
            }).then(function(response) {
                if (response.success) {
                    browser.location.reload();
//                    Dialog.alert(this, response.message, {
//                        title: 'Success',
//                        type: 'success'
//                    });
                } else {
                console.log("Hiieas errors")
//                    Dialog.alert(this, response.message, {
//                        title: 'Error',
//                        type: 'danger'
//                    });
                }
            })
        });

//        function handleFileSelect(event) {
//            const fileList = document.getElementById('fileList');
//            const files = event.target.files;
//            selectedFiles = Array.from(files);
//            displayFiles(fileList);
//        }
//
//        function displayFiles(container) {
//            container.innerHTML = '';  // Clear previous file list
//            selectedFiles.forEach((file, index) => {
//                const fileElement = document.createElement('div');
//                fileElement.className = 'file-item';
//                fileElement.innerHTML = `
//                    <span>${file.name}</span>
//                    <button type="button" class="remove_files btn btn-danger btn-sm ml-2" onclick="removeFile(${index})">Remove</button>
//                `;
//                container.appendChild(fileElement);
//            });
//        }
//
//        function removeFile(index){
//            selectedFiles.splice(index, 1);
//            displayFiles(document.getElementById('fileList'));
//            document.getElementById('files').files = createFileList(selectedFiles);
//        }
//
//        function createFileList(files) {
//            const dataTransfer = new DataTransfer();
//            files.forEach(file => dataTransfer.items.add(file));
//            return dataTransfer.files;
//        }
//
//        // Attach file selection event handler
//        $('#files').on('change', handleFileSelect);
//        $('.remove_files').on('click', removeFile)



//    });
});