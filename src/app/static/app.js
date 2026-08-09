/**
 * Resume Intelligence Platform — Frontend Application Logic
 * Zero external dependencies. Vanilla JavaScript only.
 */
(function () {
    "use strict";

    // ================================================================
    // DOM References
    // ================================================================
    const DOM = {
        jdTextarea: document.getElementById("jd-textarea"),
        jdFileInput: document.getElementById("jd-file-input"),
        resumeFileInput: document.getElementById("resume-file-input"),
        resumeFileList: document.getElementById("resume-file-list"),
        resumeUploadZone: document.getElementById("resume-upload-zone"),
        btnAnalyze: document.getElementById("btn-analyze"),
        errorBanner: document.getElementById("error-banner"),
        errorTitle: document.getElementById("error-title"),
        errorMessage: document.getElementById("error-message"),
        fileErrorsList: document.getElementById("file-errors-list"),
        loadingOverlay: document.getElementById("loading-overlay"),
        summarySection: document.getElementById("summary-section"),
        summaryTotal: document.getElementById("summary-total"),
        summaryAvg: document.getElementById("summary-avg"),
        summaryTop: document.getElementById("summary-top"),
        summaryReview: document.getElementById("summary-review"),
        rankingSection: document.getElementById("ranking-section"),
        rankingTbody: document.getElementById("ranking-tbody"),
        detailSection: document.getElementById("detail-section"),
        detailName: document.getElementById("detail-name"),
        detailOverallScore: document.getElementById("detail-overall-score"),
        qualBreakdown: document.getElementById("qualification-breakdown"),
        aiOverallScore: document.getElementById("ai-overall-score"),
        aiCategory: document.getElementById("ai-category"),
        aiConfidence: document.getElementById("ai-confidence"),
        aiSignalsContainer: document.getElementById("ai-signals-container"),
        aiDisclaimer: document.getElementById("ai-disclaimer"),
    };

    // ================================================================
    // State
    // ================================================================
    let resumeFiles = [];     // Array of { file: File, id: string }
    let analysisData = null;  // Latest analysis response from API

    // ================================================================
    // Utility Functions
    // ================================================================

    function generateId() {
        return "f_" + Math.random().toString(36).substring(2, 10);
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    function showError(title, message, fileErrors) {
        DOM.errorTitle.textContent = title;
        DOM.errorMessage.textContent = message;
        if (fileErrors && fileErrors.length > 0) {
            DOM.fileErrorsList.innerHTML = fileErrors
                .map(function (e) { return "<li><strong>" + escapeHtml(e.filename) + "</strong>: " + escapeHtml(e.error) + "</li>"; })
                .join("");
            DOM.fileErrorsList.style.display = "block";
        } else {
            DOM.fileErrorsList.style.display = "none";
        }
        DOM.errorBanner.classList.add("visible");
        DOM.errorBanner.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    function hideError() {
        DOM.errorBanner.classList.remove("visible");
    }

    function showLoading() {
        DOM.loadingOverlay.classList.add("visible");
        DOM.btnAnalyze.disabled = true;
        DOM.btnAnalyze.classList.add("loading");
    }

    function hideLoading() {
        DOM.loadingOverlay.classList.remove("visible");
        DOM.btnAnalyze.disabled = false;
        DOM.btnAnalyze.classList.remove("loading");
    }

    // ================================================================
    // Score Color Helpers
    // ================================================================

    function qualScoreColor(score) {
        if (score >= 80) return "var(--accent-success)";
        if (score >= 60) return "var(--accent-info)";
        if (score >= 40) return "var(--accent-warning)";
        return "var(--accent-danger)";
    }

    function aiScoreColor(score) {
        if (score <= 30) return "var(--accent-success)";
        if (score <= 60) return "var(--accent-warning)";
        return "var(--accent-danger)";
    }

    function aiBarClass(score) {
        if (score <= 30) return "ai-low";
        if (score <= 60) return "ai-moderate";
        return "ai-high";
    }

    function aiCategoryBadgeClass(category) {
        var cat = (category || "").toLowerCase();
        if (cat.indexOf("very high") !== -1) return "badge-very-high";
        if (cat.indexOf("high") !== -1) return "badge-high";
        if (cat.indexOf("moderate") !== -1) return "badge-moderate";
        return "badge-low";
    }

    function statusBadgeClass(status) {
        if (status === "Strong Match") return "badge-strong";
        if (status === "Good Match") return "badge-good";
        if (status === "Moderate Match") return "badge-moderate-match";
        return "badge-weak";
    }

    function componentBarGradient(score) {
        if (score >= 80) return "var(--gradient-success)";
        if (score >= 50) return "linear-gradient(135deg, #3b82f6, #2563eb)";
        if (score >= 30) return "var(--gradient-warning)";
        return "var(--gradient-danger)";
    }

    // ================================================================
    // Resume File Management
    // ================================================================

    function renderFileList() {
        if (resumeFiles.length === 0) {
            DOM.resumeFileList.innerHTML = "";
            return;
        }
        var html = resumeFiles.map(function (rf) {
            return (
                '<div class="file-item" data-id="' + rf.id + '">' +
                '  <span class="file-icon">📄</span>' +
                '  <span class="file-name">' + escapeHtml(rf.file.name) + '</span>' +
                '  <span class="file-status">Ready</span>' +
                '  <button class="remove-btn" data-id="' + rf.id + '" title="Remove">✕</button>' +
                '</div>'
            );
        }).join("");
        DOM.resumeFileList.innerHTML = html;
    }

    function addResumeFiles(fileList) {
        for (var i = 0; i < fileList.length; i++) {
            var file = fileList[i];
            // Avoid duplicates by name
            var isDuplicate = resumeFiles.some(function (rf) { return rf.file.name === file.name; });
            if (!isDuplicate) {
                resumeFiles.push({ file: file, id: generateId() });
            }
        }
        renderFileList();
    }

    function removeResumeFile(id) {
        resumeFiles = resumeFiles.filter(function (rf) { return rf.id !== id; });
        renderFileList();
    }

    // ================================================================
    // JD File Upload Handler
    // ================================================================

    DOM.jdFileInput.addEventListener("change", function () {
        if (this.files && this.files[0]) {
            var reader = new FileReader();
            reader.onload = function (e) {
                DOM.jdTextarea.value = e.target.result;
            };
            reader.readAsText(this.files[0]);
        }
    });

    // ================================================================
    // Resume File Upload Handlers
    // ================================================================

    DOM.resumeFileInput.addEventListener("change", function () {
        if (this.files && this.files.length > 0) {
            addResumeFiles(this.files);
            this.value = "";  // reset so same files can be re-selected
        }
    });

    // Drag and drop
    DOM.resumeUploadZone.addEventListener("dragover", function (e) {
        e.preventDefault();
        this.classList.add("drag-over");
    });

    DOM.resumeUploadZone.addEventListener("dragleave", function () {
        this.classList.remove("drag-over");
    });

    DOM.resumeUploadZone.addEventListener("drop", function (e) {
        e.preventDefault();
        this.classList.remove("drag-over");
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            addResumeFiles(e.dataTransfer.files);
        }
    });

    // Remove file button delegation
    DOM.resumeFileList.addEventListener("click", function (e) {
        var btn = e.target.closest(".remove-btn");
        if (btn) {
            removeResumeFile(btn.dataset.id);
        }
    });

    // ================================================================
    // Analysis Execution
    // ================================================================

    DOM.btnAnalyze.addEventListener("click", function () {
        hideError();

        // Client-side validation
        var jdText = DOM.jdTextarea.value.trim();
        if (!jdText) {
            showError("Missing Job Description", "Please enter or upload a job description before analyzing.");
            return;
        }

        if (resumeFiles.length === 0) {
            showError("No Resumes", "Please upload at least one candidate resume file.");
            return;
        }

        showLoading();

        // Build FormData
        var formData = new FormData();
        formData.append("jd_text", jdText);
        resumeFiles.forEach(function (rf) {
            formData.append("resumes", rf.file);
        });

        fetch("/api/analyze", {
            method: "POST",
            body: formData,
        })
        .then(function (response) {
            return response.json().then(function (data) {
                return { ok: response.ok, data: data };
            });
        })
        .then(function (result) {
            hideLoading();
            if (result.data.status === "success") {
                analysisData = result.data;
                renderResults(result.data);
            } else {
                showError(
                    "Analysis Failed",
                    result.data.error || "An unknown error occurred.",
                    result.data.file_errors || []
                );
            }
        })
        .catch(function (err) {
            hideLoading();
            showError("Network Error", "Could not connect to the server. Please make sure the server is running. (" + err.message + ")");
        });
    });

    // ================================================================
    // Render Results
    // ================================================================

    function renderResults(data) {
        renderSummary(data.summary);
        renderRanking(data.candidates);
        renderErrors(data.errors);

        // Auto-select first candidate
        if (data.candidates && data.candidates.length > 0) {
            renderDetail(data.candidates[0]);
            highlightRow(0);
        }

        // Smooth scroll to summary
        DOM.summarySection.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    // ---------- Summary ----------

    function renderSummary(summary) {
        DOM.summaryTotal.textContent = summary.total_candidates;
        DOM.summaryAvg.textContent = summary.average_match_score.toFixed(1) + "%";
        DOM.summaryTop.textContent = summary.top_candidate;
        DOM.summaryReview.textContent = summary.candidates_requiring_review;
        DOM.summarySection.classList.add("visible");
    }

    // ---------- Ranking ----------

    function renderRanking(candidates) {
        var html = candidates.map(function (c, idx) {
            var qScore = c.qualification_match.overall_match_score;
            var aiScore = c.ai_detection.ai_likelihood_score;
            var aiCat = c.ai_detection.category;
            var rankClass = c.rank <= 3 ? "rank-" + c.rank : "rank-other";
            var aiBarCls = aiBarClass(aiScore);
            var catBadgeCls = aiCategoryBadgeClass(aiCat);
            var statusCls = statusBadgeClass(c.status_label);

            // Short category label
            var catLabel = (aiCat || "").replace("AI-style signals", "").replace(" signals", "").trim();

            return (
                '<tr data-index="' + idx + '">' +
                '  <td><span class="rank-badge ' + rankClass + '">' + c.rank + '</span></td>' +
                '  <td class="candidate-name-cell">' + escapeHtml(c.candidate_name) + '</td>' +
                '  <td class="score-bar-cell">' +
                '    <div class="score-bar">' +
                '      <div class="score-bar-track"><div class="score-bar-fill qual" style="width:' + qScore + '%;"></div></div>' +
                '      <span class="score-value" style="color:' + qualScoreColor(qScore) + '">' + qScore.toFixed(2) + '%</span>' +
                '    </div>' +
                '  </td>' +
                '  <td class="score-bar-cell">' +
                '    <div class="score-bar">' +
                '      <div class="score-bar-track"><div class="score-bar-fill ' + aiBarCls + '" style="width:' + aiScore + '%;"></div></div>' +
                '      <span class="score-value" style="color:' + aiScoreColor(aiScore) + '">' + aiScore.toFixed(0) + '%</span>' +
                '    </div>' +
                '  </td>' +
                '  <td><span class="badge ' + catBadgeCls + '">' + escapeHtml(catLabel) + '</span></td>' +
                '  <td><span class="badge ' + statusCls + '">' + escapeHtml(c.status_label) + '</span></td>' +
                '</tr>'
            );
        }).join("");

        DOM.rankingTbody.innerHTML = html;
        DOM.rankingSection.classList.add("visible");

        // Row click handler
        DOM.rankingTbody.querySelectorAll("tr").forEach(function (tr) {
            tr.addEventListener("click", function () {
                var idx = parseInt(this.dataset.index, 10);
                if (analysisData && analysisData.candidates[idx]) {
                    renderDetail(analysisData.candidates[idx]);
                    highlightRow(idx);
                    DOM.detailSection.scrollIntoView({ behavior: "smooth", block: "start" });
                }
            });
        });

        // Animate bars after a tick
        requestAnimationFrame(function () {
            DOM.rankingTbody.querySelectorAll(".score-bar-fill").forEach(function (bar) {
                bar.style.width = bar.style.width;  // force reflow for animation
            });
        });
    }

    function highlightRow(idx) {
        DOM.rankingTbody.querySelectorAll("tr").forEach(function (tr, i) {
            tr.classList.toggle("selected", i === idx);
        });
    }

    // ---------- Errors ----------

    function renderErrors(errors) {
        if (errors && errors.length > 0) {
            showError("Some files had issues", "The following files could not be processed:", errors);
        }
    }

    // ---------- Detail Panel ----------

    function renderDetail(candidate) {
        DOM.detailSection.classList.add("visible");

        var q = candidate.qualification_match;
        var ai = candidate.ai_detection;

        DOM.detailName.textContent = candidate.candidate_name;
        DOM.detailOverallScore.textContent = q.overall_match_score.toFixed(2) + "%";
        DOM.detailOverallScore.style.color = qualScoreColor(q.overall_match_score);

        // Qualification Component Breakdown
        renderQualificationBreakdown(q.component_breakdown);

        // AI Verification Panel
        renderAIPanel(ai);
    }

    function renderQualificationBreakdown(components) {
        if (!components || components.length === 0) {
            DOM.qualBreakdown.innerHTML = '<p class="text-muted">No component data available.</p>';
            return;
        }

        var html = components.map(function (comp) {
            var barColor = componentBarGradient(comp.normalized_score);

            // Matched items
            var matchedHtml = "";
            if (comp.matched_items && comp.matched_items.length > 0) {
                matchedHtml = '<div class="items-list">' +
                    comp.matched_items.map(function (item) {
                        return '<span class="item-tag matched">✓ ' + escapeHtml(item) + '</span>';
                    }).join("") +
                    '</div>';
            }

            // Missing items
            var missingHtml = "";
            if (comp.missing_items && comp.missing_items.length > 0) {
                missingHtml = '<div class="items-list">' +
                    comp.missing_items.map(function (item) {
                        return '<span class="item-tag missing">✗ ' + escapeHtml(item) + '</span>';
                    }).join("") +
                    '</div>';
            }

            return (
                '<div class="component-card">' +
                '  <div class="component-card-header">' +
                '    <h4>' + escapeHtml(comp.component_name) + '</h4>' +
                '    <span class="component-score" style="color:' + qualScoreColor(comp.normalized_score) + '">' +
                       comp.normalized_score.toFixed(1) + '%' +
                '    </span>' +
                '  </div>' +
                '  <div class="component-bar"><div class="component-bar-fill" style="width:' + comp.normalized_score + '%; background:' + barColor + ';"></div></div>' +
                '  <span class="badge ' + statusBadge(comp.status) + '" style="margin-bottom:8px;">' + escapeHtml(comp.status) + '</span>' +
                matchedHtml +
                missingHtml +
                '  <div class="component-explanation">' + escapeHtml(comp.explanation) + '</div>' +
                '</div>'
            );
        }).join("");

        DOM.qualBreakdown.innerHTML = html;
    }

    function statusBadge(status) {
        if (status === "Meets requirement") return "badge-strong";
        if (status === "Partially meets") return "badge-moderate-match";
        if (status === "Not Applicable") return "badge-good";
        if (status === "Not Determined") return "badge-moderate";
        return "badge-weak";
    }

    function renderAIPanel(ai) {
        // Overall score
        var score = ai.ai_likelihood_score;
        DOM.aiOverallScore.textContent = score.toFixed(1) + "%";
        DOM.aiOverallScore.style.color = aiScoreColor(score);

        // Category & Confidence
        DOM.aiCategory.textContent = ai.category;
        DOM.aiCategory.style.color = aiScoreColor(score);
        DOM.aiConfidence.textContent = ai.confidence;

        // Individual signals
        var signalsHtml = "";
        if (ai.feature_breakdown && ai.feature_breakdown.length > 0) {
            signalsHtml = ai.feature_breakdown.map(function (f) {
                var barCls = aiBarClass(f.normalized_score);
                return (
                    '<div class="ai-signal-card">' +
                    '  <div class="ai-signal-header">' +
                    '    <span class="ai-signal-name">' + escapeHtml(f.feature_name) + '</span>' +
                    '    <span class="ai-signal-score" style="color:' + aiScoreColor(f.normalized_score) + '">' +
                           f.normalized_score.toFixed(1) + '%' +
                    '    </span>' +
                    '  </div>' +
                    '  <div class="ai-signal-bar"><div class="ai-signal-bar-fill ' + barCls + '" style="width:' + f.normalized_score + '%;"></div></div>' +
                    '  <div class="ai-signal-explanation">' + escapeHtml(f.explanation) + '</div>' +
                    '</div>'
                );
            }).join("");
        }
        DOM.aiSignalsContainer.innerHTML = signalsHtml;

        // Disclaimer
        DOM.aiDisclaimer.textContent = ai.disclaimer || "";
    }

    // ================================================================
    // Initialization
    // ================================================================

    // Ensure file-list delegated click works on load
    renderFileList();

})();
