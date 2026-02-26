/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { xml } from "@odoo/owl";
import { jsonrpc } from "@web/core/network/rpc_service";
import { getDataURLFromFile } from "@web/core/utils/urls";

export const portalmyinvoicetemplates = publicWidget.Widget.extend({
    selector: '.o_portal_my_invoice_templates',
    events: {
        'click .btn-secondary': 'goBack',
        'click .btn-primary': 'uploadDocuments',
        'change input#files': '_onChangeSlideUpload',
        'mousedown #overlay-canvas': 'startDrawing',
        'mouseup #overlay-canvas': 'stopDrawing',
        'mousemove #overlay-canvas': 'draw'
    },
    init() {
        this._super(...arguments);
        this.isDrawing = false; // Initialize drawing state
            this.ctx = document.getElementById('overlay-canvas').getContext('2d');
            this.ctx.strokeStyle = 'red'; // Color of the annotations
            this.ctx.lineWidth = 2; //
    },
    async uploadDocuments() {
        console.log("Uploading...");
        this.renderPdf(this.pdfUrl);
    },
    async _onChangeSlideUpload(ev) {
        const data = await getDataURLFromFile(ev.target.files[0]);
        this.pdfUrl = data.split(',', 2)[1]; // Get base64 part
    },
    renderPdf: function(pdfUrl) {
        // Ensure pdfUrl is correct
        const loadingTask = window.pdfjsLib.getDocument({ data: atob(pdfUrl) });

        loadingTask.promise.then(pdf => {
            console.log('PDF loaded');
            // Fetch the first page
            return pdf.getPage(1);
        }).then(page => {
            console.log('Page loaded');
            const scale = 1.5; // Adjust scale for zoom
            const viewport = page.getViewport({ scale: scale });

            // Prepare canvas using PDF page dimensions
            const canvas = document.getElementById('pdf-canvas');
            const context = canvas.getContext('2d');
            canvas.height = viewport.height;
            canvas.width = viewport.width;

            // Render PDF page into canvas context
            const renderContext = {
                canvasContext: context,
                viewport: viewport
            };
            return page.render(renderContext).promise; // Ensure this returns a promise
        }).then(() => {
            console.log('Page rendered');
            // After rendering, set up the drawing context
            const overlayCanvas = document.getElementById('overlay-canvas');
            overlayCanvas.width = document.getElementById('pdf-canvas').width;
            overlayCanvas.height = document.getElementById('pdf-canvas').height;
            this.ctx = overlayCanvas.getContext('2d');
            this.ctx.strokeStyle = 'red'; // Color of the annotations
            this.ctx.lineWidth = 2; // Width of the annotations
            document.getElementById('overlay-canvas').addEventListener('mousemove', function(event) {
                console.log('Mouse move detected at: ', event.offsetX, event.offsetY);
                this.ctx = document.getElementById('overlay-canvas').getContext('2d');
                if (!this.isDrawing) return; // If not drawing, do nothing
                this.ctx.lineTo(event.offsetX, event.offsetY); // Draw line to mouse position
                this.ctx.stroke(); // Render the line
            });

//            document.getElementById('overlay-canvas').addEventListener('mousemove', function(event) {
//
//            });
            document.getElementById('overlay-canvas').addEventListener('mousedown', function(event) {
                        this.isDrawing = true; // Start drawing
            this.ctx.beginPath(); // Begin a new path
        this.ctx.moveTo(event.offsetX, event.offsetY); // Move to mouse position
        console.log('Mouse move detected at: ', event.offsetX, event.offsetY);
            });
            document.getElementById('overlay-canvas').addEventListener('mouseup', function(event) {
                        this.isDrawing = false; // Stop drawing
        this.ctx.closePath(); // Close the path
            });

        }).catch(error => {
            console.log('Error loading PDF: ' + error);
        });
    },
//    startDrawing: function(event) {
//        this.isDrawing = true; // Start drawing
//        this.ctx.beginPath(); // Begin a new path
//        this.ctx.moveTo(event.offsetX, event.offsetY); // Move to mouse position
//        console.log('Mouse move detected at: ', event.offsetX, event.offsetY);
//    },
//    stopDrawing: function() {
//        this.isDrawing = false; // Stop drawing
//        this.ctx.closePath(); // Close the path
//    },
//    draw: function(event) {
//        if (!this.isDrawing) return; // If not drawing, do nothing
//        this.ctx.lineTo(event.offsetX, event.offsetY); // Draw line to mouse position
//        this.ctx.stroke(); // Render the line
//    },
    goBack: function() {
        window.history.back();  // Go back to the previous page
    },
});

publicWidget.registry.portalmyinvoicetemplates = portalmyinvoicetemplates;
