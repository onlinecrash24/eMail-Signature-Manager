/* ============================================
   Email Signature Manager - Template Editor
   Requires: CodeMirror 5 (loaded via CDN)
   ============================================ */

(function () {
    'use strict';

    // ---- Sample data for live preview (German example) ----
    var sampleData = {
        vorname: 'Max',
        nachname: 'Mustermann',
        titel: 'Dr.',
        durchwahl: '0441 12345 - 422',
        email: 'max.mustermann@firma.de',
        optionale_rufnummer: '0175 1234567',
        abteilung: 'IT-Abteilung',
        firma: getMetaText('tenant-name', 'Musterfirma GmbH'),
        strasse: getMetaText('tenant-street', 'Musterstraße 1'),
        plz: getMetaText('tenant-zip', '26121'),
        ort: getMetaText('tenant-city', 'Oldenburg'),
        telefon: getMetaText('tenant-phone', '0441 12345 - 0'),
        fax: getMetaText('tenant-fax', '0441 12345 - 999'),
        website: getMetaText('tenant-website', 'www.firma.de'),
        logo_url: getMetaText('tenant-logo', '')
    };

    function getMetaText(id, fallback) {
        var el = document.getElementById(id);
        return el ? el.textContent.trim() : fallback;
    }

    // ---- CodeMirror editor instances ----
    var htmlEditor = null;
    var txtEditor = null;
    var rtfEditor = null;

    // ---- Debounce utility ----
    function debounce(fn, delay) {
        var timer = null;
        return function () {
            var context = this;
            var args = arguments;
            clearTimeout(timer);
            timer = setTimeout(function () {
                fn.apply(context, args);
            }, delay);
        };
    }

    // ---- Variable replacement engine ----
    function replaceVariables(template, data) {
        if (!template) return '';

        var processed = template;

        // Handle Jinja2 {% if variable %}...{% endif %} (with optional {% else %})
        // Repeat to handle nested blocks
        for (var i = 0; i < 5; i++) {
            processed = processed.replace(
                /\{%[-\s]*if\s+(\w+)\s*%\}([\s\S]*?)\{%[-\s]*endif\s*%\}/g,
                function (match, varName, content) {
                    var value = data[varName];
                    var hasValue = value && value.toString().trim() !== '';

                    // Check for {% else %}
                    var parts = content.split(/\{%[-\s]*else\s*%\}/);
                    if (hasValue) {
                        return replaceVariables(parts[0], data);
                    } else {
                        return parts.length > 1 ? replaceVariables(parts[1], data) : '';
                    }
                }
            );
        }

        // Handle {{#if variable}}content{{/if}} (alternative syntax)
        processed = processed.replace(
            /\{\{#if\s+(\w+)\}\}([\s\S]*?)\{\{\/if\}\}/g,
            function (match, varName, content) {
                var value = data[varName];
                if (value && value.toString().trim() !== '') {
                    return replaceVariables(content, data);
                }
                return '';
            }
        );

        // Replace {{variable}} placeholders
        processed = processed.replace(
            /\{\{(\w+)\}\}/g,
            function (match, varName) {
                return data[varName] !== undefined ? data[varName] : '';
            }
        );

        return processed;
    }

    // ---- Strip basic RTF tags for preview ----
    function stripRtf(rtfText) {
        if (!rtfText) return '';

        var result = rtfText;
        // Remove RTF header/footer
        result = result.replace(/^\{\\rtf[^}]*\}?/i, '');
        result = result.replace(/\{\\[^}]+\}/g, '');
        // Remove control words
        result = result.replace(/\\[a-z]+\d*\s?/gi, '');
        // Remove remaining braces
        result = result.replace(/[{}]/g, '');
        // Clean up whitespace
        result = result.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
        result = result.trim();

        return result || rtfText;
    }

    // ---- Update the preview pane ----
    function updatePreview(format) {
        var activeFormat = format || getActiveFormat();
        var editor = getEditorByFormat(activeFormat);
        if (!editor) return;

        var rawContent = editor.getValue();
        var rendered = replaceVariables(rawContent, sampleData);

        switch (activeFormat) {
            case 'html':
                var iframe = document.getElementById('preview-iframe');
                if (iframe) {
                    iframe.srcdoc = rendered;
                }
                break;

            case 'txt':
                var preEl = document.getElementById('preview-txt');
                if (preEl) {
                    preEl.textContent = rendered;
                }
                break;

            case 'rtf':
                var rtfPreEl = document.getElementById('preview-rtf');
                if (rtfPreEl) {
                    rtfPreEl.textContent = stripRtf(rendered);
                }
                break;
        }
    }

    function getActiveFormat() {
        var activeTab = document.querySelector('#editorTabs .nav-link.active');
        if (!activeTab) return 'html';
        var href = activeTab.getAttribute('href') || activeTab.getAttribute('data-bs-target') || '';
        if (href.indexOf('txt') !== -1) return 'txt';
        if (href.indexOf('rtf') !== -1) return 'rtf';
        return 'html';
    }

    function getEditorByFormat(format) {
        switch (format) {
            case 'html': return htmlEditor;
            case 'txt': return txtEditor;
            case 'rtf': return rtfEditor;
            default: return htmlEditor;
        }
    }

    // ---- Initialize CodeMirror editors ----
    function initEditors() {
        var htmlTextarea = document.getElementById('html-editor');
        var txtTextarea = document.getElementById('txt-editor');
        var rtfTextarea = document.getElementById('rtf-editor');

        if (htmlTextarea && typeof CodeMirror !== 'undefined') {
            htmlEditor = CodeMirror.fromTextArea(htmlTextarea, {
                mode: 'htmlmixed',
                theme: 'monokai',
                lineNumbers: true,
                lineWrapping: true,
                matchBrackets: true,
                autoCloseTags: true,
                autoCloseBrackets: true,
                indentUnit: 2,
                tabSize: 2,
                indentWithTabs: false,
                extraKeys: {
                    'Ctrl-Space': 'autocomplete',
                    'Ctrl-S': function () { syncAndSave(); }
                }
            });

            htmlEditor.on('change', debounce(function () {
                updatePreview('html');
            }, 500));
        }

        if (txtTextarea && typeof CodeMirror !== 'undefined') {
            txtEditor = CodeMirror.fromTextArea(txtTextarea, {
                mode: 'text/plain',
                theme: 'monokai',
                lineNumbers: true,
                lineWrapping: true,
                indentUnit: 2,
                tabSize: 2,
                extraKeys: {
                    'Ctrl-S': function () { syncAndSave(); }
                }
            });

            txtEditor.on('change', debounce(function () {
                updatePreview('txt');
            }, 500));
        }

        if (rtfTextarea && typeof CodeMirror !== 'undefined') {
            rtfEditor = CodeMirror.fromTextArea(rtfTextarea, {
                mode: 'text/plain',
                theme: 'monokai',
                lineNumbers: true,
                lineWrapping: true,
                indentUnit: 2,
                tabSize: 2,
                extraKeys: {
                    'Ctrl-S': function () { syncAndSave(); }
                }
            });

            rtfEditor.on('change', debounce(function () {
                updatePreview('rtf');
            }, 500));
        }

        // Initial preview after a short delay to let editors render
        setTimeout(function () {
            updatePreview();
        }, 300);
    }

    // ---- Tab switching ----
    function initTabSwitching() {
        var tabLinks = document.querySelectorAll('#editorTabs .nav-link');
        tabLinks.forEach(function (tab) {
            tab.addEventListener('shown.bs.tab', function () {
                var format = getActiveFormat();
                var editor = getEditorByFormat(format);
                if (editor) {
                    // CodeMirror needs refresh when tab becomes visible
                    setTimeout(function () {
                        editor.refresh();
                        updatePreview(format);
                    }, 50);
                }
            });
        });
    }

    // ---- Copy variable to clipboard ----
    function initCopyButtons() {
        document.addEventListener('click', function (e) {
            var btn = e.target.closest('.btn-copy-var');
            if (!btn) return;

            e.preventDefault();
            var varText = btn.getAttribute('data-variable');
            if (!varText) return;

            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(varText).then(function () {
                    showCopied(btn);
                }).catch(function () {
                    fallbackCopy(varText, btn);
                });
            } else {
                fallbackCopy(varText, btn);
            }
        });
    }

    function fallbackCopy(text, btn) {
        var textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            showCopied(btn);
        } catch (err) {
            console.warn('Copy failed:', err);
        }
        document.body.removeChild(textarea);
    }

    function showCopied(btn) {
        var originalText = btn.innerHTML;
        btn.classList.add('copied');
        btn.innerHTML = '<i class="bi bi-check"></i>';
        setTimeout(function () {
            btn.classList.remove('copied');
            btn.innerHTML = originalText;
        }, 1500);
    }

    // ---- Sync CodeMirror content back to textareas before form submit ----
    function syncEditors() {
        if (htmlEditor) htmlEditor.save();
        if (txtEditor) txtEditor.save();
        if (rtfEditor) rtfEditor.save();
    }

    function syncAndSave() {
        syncEditors();
        var form = document.getElementById('template-form');
        if (form) {
            form.submit();
        }
    }

    function initFormSync() {
        var form = document.getElementById('template-form');
        if (form) {
            form.addEventListener('submit', function () {
                syncEditors();
            });
        }
    }

    // ---- SMB connection test ----
    function initSmbTest() {
        var testBtn = document.getElementById('btn-test-smb');
        if (!testBtn) return;

        testBtn.addEventListener('click', function (e) {
            e.preventDefault();

            var resultDiv = document.getElementById('smb-test-result');
            var server = document.getElementById('smb_server');
            var share = document.getElementById('smb_share');
            var username = document.getElementById('smb_username');
            var password = document.getElementById('smb_password');
            var domain = document.getElementById('smb_domain');

            if (!server || !server.value.trim()) {
                showSmbResult(resultDiv, false, 'Bitte geben Sie einen Server an.');
                return;
            }

            // Set testing state
            testBtn.classList.add('testing');
            testBtn.classList.remove('test-success', 'test-error');
            testBtn.innerHTML = '<i class="bi bi-arrow-repeat"></i> Teste...';

            if (resultDiv) {
                resultDiv.classList.remove('show', 'result-success', 'result-error');
            }

            var payload = {
                server: server.value.trim(),
                share: share ? share.value.trim() : '',
                username: username ? username.value.trim() : '',
                password: password ? password.value : '',
                domain: domain ? domain.value.trim() : ''
            };

            var csrfToken = document.querySelector('meta[name="csrf-token"]');
            var headers = {
                'Content-Type': 'application/json'
            };
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken.getAttribute('content');
            }

            fetch('/api/test-smb', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(payload)
            })
                .then(function (response) { return response.json(); })
                .then(function (data) {
                    testBtn.classList.remove('testing');
                    if (data.success) {
                        testBtn.classList.add('test-success');
                        testBtn.innerHTML = '<i class="bi bi-check-circle"></i> Verbunden';
                        showSmbResult(resultDiv, true, data.message || 'Verbindung erfolgreich hergestellt.');
                    } else {
                        testBtn.classList.add('test-error');
                        testBtn.innerHTML = '<i class="bi bi-x-circle"></i> Fehlgeschlagen';
                        showSmbResult(resultDiv, false, data.message || 'Verbindung fehlgeschlagen.');
                    }
                    resetTestButton(testBtn);
                })
                .catch(function (err) {
                    testBtn.classList.remove('testing');
                    testBtn.classList.add('test-error');
                    testBtn.innerHTML = '<i class="bi bi-x-circle"></i> Fehler';
                    showSmbResult(resultDiv, false, 'Netzwerkfehler: ' + err.message);
                    resetTestButton(testBtn);
                });
        });
    }

    function showSmbResult(resultDiv, success, message) {
        if (!resultDiv) return;
        resultDiv.className = 'smb-test-result show ' + (success ? 'result-success' : 'result-error');
        resultDiv.innerHTML = (success ? '<i class="bi bi-check-circle-fill me-1"></i>' : '<i class="bi bi-exclamation-triangle-fill me-1"></i>') + message;
    }

    function resetTestButton(btn) {
        setTimeout(function () {
            btn.classList.remove('test-success', 'test-error');
            btn.innerHTML = '<i class="bi bi-plug"></i> Verbindung testen';
        }, 4000);
    }

    // ---- Auto-dismiss flash messages ----
    function initFlashDismiss() {
        var alerts = document.querySelectorAll('.alert-flash');
        alerts.forEach(function (alert) {
            setTimeout(function () {
                var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                if (bsAlert) {
                    bsAlert.close();
                }
            }, 5000);
        });
    }

    // ---- Insert variable at cursor position ----
    function initVariableInsert() {
        document.addEventListener('dblclick', function (e) {
            var btn = e.target.closest('.btn-copy-var');
            if (!btn) return;

            var varText = btn.getAttribute('data-variable');
            if (!varText) return;

            var editor = getEditorByFormat(getActiveFormat());
            if (editor) {
                var cursor = editor.getCursor();
                editor.replaceRange(varText, cursor);
                editor.focus();
            }
        });
    }

    // ---- Initialize everything ----
    function init() {
        initEditors();
        initTabSwitching();
        initCopyButtons();
        initFormSync();
        initSmbTest();
        initFlashDismiss();
        initVariableInsert();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
