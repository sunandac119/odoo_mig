odoo.define('omni_print.download', function (require) {
    "use strict";

    var ajax = require('web.ajax');
    var _get_file = ajax.get_file;

    function downloadFile(blob, filename, mimetype) {
        var url = window.URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        window.URL.revokeObjectURL(url);
    }

    function sendToPrinter(data, proxyUrl) {
        var formData = new FormData();
        formData.append("file", data.file, data.filename);
        formData.append("reportName", data.reportName);
        formData.append("reportTitle", data.reportTitle);
        formData.append("docNames", data.docNames);

        return fetch(proxyUrl, {
            method: "POST",
            body: formData,
            headers: {
                "Access-Control-Allow-Origin": "*",
                "Accept-Referrer-Policy": "no-referrer",
            },
        });
    }

    function handleResponse(response, reportType) {
        if (!response.ok) {
            return response.text().then(function (text) {
                return parseError(text, response.status);
            });
        }

        var filename = parseContentDisposition(response.headers.get("Content-Disposition"));
        return response.blob().then(function (blob) {
            var mimetype = blob.type;
            if (mimetype === "text/html" || !filename) {
                return Promise.reject(new Error("Invalid MIME type or filename missing."));
            }

            function getDecodedHeader(key) {
                return response.headers.get(key) && decodeURIComponent(response.headers.get(key));
            }

            var printData = {
                file: blob,
                filename: filename,
                reportName: getDecodedHeader("X-Report-Name") || "",
                reportTitle: getDecodedHeader("X-Report-Title") || "",
                docNames: getDecodedHeader("X-Report-Docnames") || removeExtension(filename) || ""
            };

            var format = reportType === "qweb-pdf" ? "pdf" : "zpl";
            var proxyUrl = "http://127.0.0.1:32276/print/" + format;
            return sendToPrinter(printData, proxyUrl)
                .then(function (uploadResponse) {
                    if (uploadResponse && !uploadResponse.ok) {
                        return uploadResponse.text().then(function (text) {
                            return Promise.reject(new Error(text));
                        });
                    }
                    return Promise.resolve();
                }).then(function () {
                    return Promise.resolve(filename);
                }).catch(function (error) {
                    console.log('print error = ', error);
                    downloadFile(blob, filename, mimetype);
                    return Promise.resolve(filename);
                });
        });
    }

    function parseError(text, status) {
        var doc = new DOMParser().parseFromString(text, "text/html");
        var nodes = doc.body.children.length ? doc.body.children : [doc.body];
        var error = {
            message: "Arbitrary Uncaught Python Exception",
            data: {
                debug: status + "\n" + nodes[0].textContent + "\n" + (nodes.length > 1 ? nodes[1].textContent : ""),
            },
        };
        return Promise.reject(error);
    }

    function parseContentDisposition(contentDisposition) {
        if (!contentDisposition) {
            return null;
        }

        var filenameRfc5987Regex = /filename\*=([^';]+)'([^';]*)'([^';]*)/;
        var matchesRfc5987 = filenameRfc5987Regex.exec(contentDisposition);
        if (matchesRfc5987 && matchesRfc5987.length === 4) {
            var encodedFilename = matchesRfc5987[3];
            var decodedFilename = decodeURIComponent(encodedFilename);
            return decodedFilename;
        }

        var filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
        var matches = filenameRegex.exec(contentDisposition);
        if (matches != null && matches[1]) {
            var filename = matches[1].replace(/['"]/g, "");
            return decodeURIComponent(filename);
        }

        return null;
    }

    function removeExtension(filename) {
        return filename.replace(/\.[^/.]+$/, "");
    }

    // Override the default download function
    ajax.get_file = function (options) {
        if (!options.url || options.url !== "/report/download") {
            return _get_file.apply(this, arguments);
        }

        var data = JSON.parse(options.data.data);
        var reportType = data[1];
        if (reportType !== "qweb-pdf" && reportType !== "qweb-text") {
            return _get_file.apply(this, arguments);
        }

        var formData = new FormData(options.form || undefined);
        if (!options.form) {
            Object.entries(options.data).forEach(function (entry) {
                formData.append(entry[0], entry[1]);
            });
        }
        formData.append("token", "dummy-because-api-expects-one");
        if (window.odoo && window.odoo.csrf_token) {
            formData.append("csrf_token", window.odoo.csrf_token);
        }

        return fetch(options.form ? options.form.action : options.url, {
            method: options.form ? options.form.method : "POST",
            body: formData,
        }).then(function (response) {
            return handleResponse(response, reportType);
        }).catch(function (error) {
            return Promise.reject({message: "Connection lost", event: error});
        }).finally(function () {
            if (options.success) { options.success(); }
            if (options.complete) { options.complete(); }
        });
    };
});