// ==========================================
// LABFLOW - COMPLETE FRONTEND APPLICATION
// ==========================================

const $ = (id) => document.getElementById(id);

let pt = null;
let pc = null;
let st = null;
let dt = null;

// ==========================================
// UTILITIES
// ==========================================

function msg(message) {
    const toast = $("toast");

    if (!toast) {
        alert(message);
        return;
    }

    toast.textContent = message;
    toast.classList.add("show");

    clearTimeout(window.toastTimer);

    window.toastTimer = setTimeout(() => {
        toast.classList.remove("show");
    }, 3500);
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[char]);
}

async function req(url, options = {}) {
    const headers = {
        ...(options.headers || {})
    };

    if (options.auth) {
        headers.Authorization = "Bearer " + options.auth;
    }

    let body = options.body;

    if (body && !(body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
        body = JSON.stringify(body);
    }

    const response = await fetch(url, {
        method: options.method || "GET",
        headers,
        body
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(
            data.detail || data.message || "Request failed"
        );
    }

    return data;
}

// ==========================================
// NAVIGATION - PATIENT / FRONT DESK / DOCTOR
// ==========================================

document.querySelectorAll("nav button[data-tab]").forEach(button => {
    button.addEventListener("click", () => {
        const target = button.dataset.tab;

        $("patient").classList.toggle(
            "hide",
            target !== "patient"
        );

        $("staff").classList.toggle(
            "hide",
            target !== "staff"
        );

        $("doctor").classList.toggle("hide", target !== "doctor");
        $("pathologist").classList.toggle("hide", target !== "pathologist");

        document.querySelectorAll("nav button[data-tab]").forEach(btn => {
            btn.classList.toggle("active", btn === button);
        });
    });
});

// ==========================================
// PATIENT - SEND OTP
// ==========================================

$("send").addEventListener("click", async () => {
    try {
        const mobile = $("mobile").value.trim();

        if (!/^\d{10,}$/.test(mobile)) {
            msg("Please enter a valid mobile number.");
            return;
        }

        const button = $("send");

        button.disabled = true;
        button.textContent = "Sending...";

        await req("/api/patient/request-otp", {
            method: "POST",
            body: { mobile }
        });

        alert("Demo OTP is printed in your VS Code terminal.");

    } catch (error) {
        msg(error.message);

    } finally {
        $("send").disabled = false;
        $("send").textContent = "Send OTP →";
    }
});

// ==========================================
// PATIENT - VERIFY OTP
// ==========================================

$("verify").addEventListener("click", async () => {
    try {
        const mobile = $("mobile").value.trim();
        const otp = $("otp").value.trim();

        if (!/^\d{6}$/.test(otp)) {
            msg("Enter the 6-digit OTP.");
            return;
        }

        const button = $("verify");

        button.disabled = true;
        button.textContent = "Verifying...";

        const data = await req("/api/patient/verify-otp", {
            method: "POST",
            body: { mobile, otp }
        });

        pt = data.token;

        if (!data.profiles || data.profiles.length === 0) {
            msg("No patient profiles found.");
            return;
        }

        await showPatientProfiles(data.profiles);

        msg("OTP verified successfully.");

    } catch (error) {
        msg(error.message);

    } finally {
        $("verify").disabled = false;
        $("verify").textContent = "Verify OTP →";
    }
});

// ==========================================
// PATIENT - PRIVACY CONSENT
// ==========================================

async function showPatientProfiles(profiles) {
    const status = await req(
        "/api/patient/consent-status",
        { auth: pt }
    );

    const consentMap = new Map(
        status.profiles.map(item => [
            item.patient_code,
            item
        ])
    );

    $("profiles").innerHTML = `
        <h4>Patient Profiles & Privacy Consent</h4>

        <p class="hint">
            Each patient profile requires separate consent before
            diagnostic reports can be accessed.
        </p>

        ${profiles.map(profile => {
            const code = escapeHTML(profile.patient_code);
            const name = escapeHTML(profile.name);
            const consent = consentMap.get(profile.patient_code);
            const accepted = consent && consent.consented;

            return `
                <article class="profile-consent-card">
                    <h4>${name}</h4>
                    <small>${code}</small>

                    ${accepted ? `
                        <p class="hint">Privacy consent recorded.</p>
                        <button
                            type="button"
                            class="profile-button"
                            data-code="${code}">
                            Open Reports →
                        </button>
                    ` : `
                        <p>
                            LABFLOW processes this patient's personal
                            and diagnostic information to provide report
                            access, report delivery, clinical operations,
                            and security/audit records.
                        </p>

                        <label>
                            <input
                                type="checkbox"
                                data-consent-check="${code}">
                            I voluntarily consent to this processing
                            for the purposes described above.
                        </label>

                        <p class="hint">
                            Policy version: LABFLOW-DPDP-1.0
                        </p>

                        <button
                            type="button"
                            data-consent-accept="${code}"
                            disabled>
                            Accept & Continue →
                        </button>
                    `}
                </article>
            `;
        }).join("")}
    `;

    $("profiles").querySelectorAll("[data-code]").forEach(button => {
        button.addEventListener("click", () => {
            orders(button.dataset.code);
        });
    });

    $("profiles").querySelectorAll("[data-consent-check]").forEach(check => {
        check.addEventListener("change", () => {
            const code = check.dataset.consentCheck;
            const button = $("profiles").querySelector(
                `[data-consent-accept="${code}"]`
            );

            if (button) {
                button.disabled = !check.checked;
            }
        });
    });

    $("profiles").querySelectorAll("[data-consent-accept]").forEach(button => {
        button.addEventListener("click", async () => {
            const code = button.dataset.consentAccept;
            const checkbox = $("profiles").querySelector(
                `[data-consent-check="${code}"]`
            );

            if (!checkbox || !checkbox.checked) {
                msg("Please provide explicit consent first.");
                return;
            }

            button.disabled = true;
            button.textContent = "Recording consent...";

            try {
                await req("/api/patient/consent", {
                    method: "POST",
                    auth: pt,
                    body: {
                        patient_code: code,
                        accepted: true
                    }
                });

                msg("Consent recorded successfully.");
                await orders(code);

            } catch (error) {
                msg(error.message);
                button.disabled = false;
                button.textContent = "Accept & Continue →";
            }
        });
    });
}

// ==========================================
// PATIENT - LOAD ORDERS
// ==========================================

async function orders(code) {
    try {
        pc = code;

        const data = await req(
            "/api/patient/orders?patient_code=" +
            encodeURIComponent(code),
            { auth: pt }
        );

        $("orders").classList.remove("hide");
        $("report").innerHTML = "";

        if (!Array.isArray(data) || data.length === 0) {
            $("orderList").innerHTML = "<p>No orders found.</p>";
            return;
        }

        $("orderList").innerHTML = data.map(order => {
            const ref = String(order.order_ref);

            const ready =
                String(order.status).trim().toLowerCase() === "ready";

            return `
                <div class="order">

                    <b>${escapeHTML(order.test_name)}</b>

                    <small>
                        ${escapeHTML(ref)}
                        · ${escapeHTML(order.status)}
                    </small>

                    <div
                        class="order-actions"
                        style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px">

                        <button
                            type="button"
                            ${ready ? "" : "disabled"}
                            data-report="${escapeHTML(ref)}">

                            View Report

                        </button>

                        <button
                            type="button"
                            ${ready ? "" : "disabled"}
                            data-download="${escapeHTML(ref)}">

                            ⬇ Download PDF

                        </button>

                        <button
                            type="button"
                            ${ready ? "" : "disabled"}
                            data-secure="${escapeHTML(ref)}">

                            Create Secure Link

                        </button>

                    </div>

                </div>
            `;
        }).join("");

        $("orderList").querySelectorAll("[data-report]").forEach(button => {
            button.addEventListener("click", () => {
                report(button.dataset.report);
            });
        });

        $("orderList").querySelectorAll("[data-download]").forEach(button => {
            button.addEventListener("click", () => {
                downloadPatientPdf(button.dataset.download);
            });
        });

        $("orderList").querySelectorAll("[data-secure]").forEach(button => {
            button.addEventListener("click", () => {
                secure(button.dataset.secure);
            });
        });

        msg("Patient orders loaded.");

    } catch (error) {
        msg(error.message);
    }
}

// ==========================================
// PATIENT - VIEW REPORT
// ==========================================

async function report(ref, language = "en") {
    try {
        const data = await req(
            `/api/patient/report/${encodeURIComponent(ref)}?patient_code=${encodeURIComponent(pc)}&language=${encodeURIComponent(language)}`,
            { auth: pt }
        );

        const summary = data.summary || {};
        const values = data.values || [];

        const criticalSuppressed =
            summary.status === "SUPPRESSED_CRITICAL";

        $("report").innerHTML = `
            <article class="report-card">

                <p class="eyebrow">DIAGNOSTIC REPORT</p>

                <h2>${escapeHTML(data.test_name)}</h2>

                <p>
                    Order Reference:
                    <b>${escapeHTML(data.order_ref)}</b>
                </p>

                <p>
                    Doctor:
                    ${escapeHTML(data.doctor || "Not specified")}
                </p>

                <hr>

                <label for="summaryLanguage">
    Summary Language
</label>

<select
    id="summaryLanguage"
    style="width:100%;padding:12px;border:1px solid #d4dfe2;border-radius:8px;margin-bottom:16px">

    <option value="en" ${language === "en" ? "selected" : ""}>English</option>
    <option value="hi" ${language === "hi" ? "selected" : ""}>हिन्दी</option>
    <option value="te" ${language === "te" ? "selected" : ""}>తెలుగు</option>

</select>
<h3>Clinical Summary</h3>

                <p>
                    ${escapeHTML(
                        summary.text || "Summary unavailable."
                    )}
                </p>

                <small>
                    ${escapeHTML(summary.status || "")}
                    ·
                    ${escapeHTML(summary.source || "")}
                </small>

                <h3>Test Results</h3>

                <div class="table-wrap">

                    <table>

                        <thead>
                            <tr>
                                <th>Parameter</th>
                                <th>Value</th>
                                <th>Unit</th>
                                <th>Reference Range</th>
                                <th>Flag</th>
                            </tr>
                        </thead>

                        <tbody>

                            ${values.map(value => `
                                <tr>
                                    <td>${escapeHTML(value.analyte)}</td>
                                    <td>${escapeHTML(value.value)}</td>
                                    <td>${escapeHTML(value.unit)}</td>
                                    <td>${escapeHTML(value.range)}</td>
                                    <td>${escapeHTML(value.flag)}</td>
                                </tr>
                            `).join("")}

                        </tbody>

                    </table>

                </div>

                <button
                    type="button"
                    onclick="downloadPatientPdf('${escapeHTML(ref)}')">

                    ⬇ Download PDF

                </button>

                ${
                    criticalSuppressed
                    ? `
                        <div class="result" style="margin-top:20px">

                            <b>Feedback unavailable</b>

                            <p>
                                Automated feedback is disabled for
                                safety-suppressed critical summaries.
                                Please contact the laboratory team.
                            </p>

                        </div>
                    `
                    : `
                        <hr>

                        <section id="feedbackSection">

                            <h3>Summary Feedback</h3>

                            <p>
                                Help us improve the clarity and accuracy
                                of your diagnostic summary.
                            </p>

                            <label for="feedbackCategory">
                                Feedback Category
                            </label>

                            <select
                                id="feedbackCategory"
                                style="width:100%;padding:12px;border:1px solid #d4dfe2;border-radius:8px;margin-bottom:12px">

                                <option value="">Select a reason</option>

                                <option value="Inaccurate information">
                                    Inaccurate information
                                </option>

                                <option value="Unclear explanation">
                                    Unclear explanation
                                </option>

                                <option value="Other">
                                    Other
                                </option>

                            </select>

                            <label for="feedbackComment">
                                Additional Comments (Optional)
                            </label>

                            <textarea
                                id="feedbackComment"
                                maxlength="1000"
                                rows="4"
                                placeholder="Tell us more about your feedback..."
                                style="width:100%;padding:12px;border:1px solid #d4dfe2;border-radius:8px;font:inherit;resize:vertical"></textarea>

                            <button
                                type="button"
                                id="submitFeedback">

                                Submit Feedback

                            </button>

                            <p
                                id="feedbackMessage"
                                class="hint"
                                aria-live="polite">
                            </p>

                        </section>
                    `
                }

            </article>
        `;
        $("summaryLanguage").addEventListener("change", (event) => {
            report(ref, event.target.value);
        });

        if (!criticalSuppressed) {
            $("submitFeedback").addEventListener("click", () => {
                submitFeedback(ref);
            });
        }

        $("report").scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    } catch (error) {
        msg(error.message);
    }
}

// ==========================================
// PATIENT - SUBMIT SUMMARY FEEDBACK
// ==========================================

async function submitFeedback(ref) {
    const button = $("submitFeedback");
    const message = $("feedbackMessage");

    try {
        const category = $("feedbackCategory").value;
        const comment = $("feedbackComment").value.trim();

        if (!category) {
            message.textContent =
                "Please select a feedback category.";
            return;
        }

        button.disabled = true;
        button.textContent = "Submitting...";

        const data = await req(
            `/api/patient/feedback/${encodeURIComponent(ref)}`,
            {
                method: "POST",
                auth: pt,
                body: {
                    patient_code: pc,
                    category,
                    comment
                }
            }
        );

        message.textContent =
            data.message || "Feedback submitted successfully.";

        $("feedbackCategory").disabled = true;
        $("feedbackComment").disabled = true;

        button.textContent = "Feedback Submitted";

        msg("Feedback submitted successfully.");

    } catch (error) {
        message.textContent = error.message;

        button.disabled = false;
        button.textContent = "Submit Feedback";
    }
}

// ==========================================
// PATIENT - DOWNLOAD PDF
// ==========================================

async function downloadPatientPdf(ref) {
    try {
        const response = await fetch(
            `/api/patient/pdf/${encodeURIComponent(ref)}?patient_code=${encodeURIComponent(pc)}`,
            {
                headers: {
                    Authorization: "Bearer " + pt
                }
            }
        );

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));

            throw new Error(
                error.detail || "PDF download failed."
            );
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

        const link = document.createElement("a");

        link.href = url;
        link.download = ref + ".pdf";

        document.body.appendChild(link);
        link.click();
        link.remove();

        URL.revokeObjectURL(url);

        msg("PDF download started.");

    } catch (error) {
        msg(error.message);
    }
}

// ==========================================
// PATIENT - SECURE LINK
// ==========================================

async function secure(ref) {
    try {
        const data = await req(
            `/api/patient/secure-link/${encodeURIComponent(ref)}`,
            {
                method: "POST",
                auth: pt,
                body: {
                    patient_code: pc
                }
            }
        );

        const fullURL = location.origin + data.url;

        $("report").insertAdjacentHTML(
            "beforeend",
            `
            <article>

                <h3>Secure Report Link</h3>

                <input
                    type="text"
                    readonly
                    value="${escapeHTML(fullURL)}"
                    style="width:100%">

                <p>
                    Expires in
                    ${escapeHTML(data.expires_hours)}
                    hours.
                </p>

            </article>
            `
        );

        msg("Secure link created.");

    } catch (error) {
        msg(error.message);
    }
}

// ==========================================
// FRONT DESK - STAFF LOGIN
// ==========================================

$("signin").addEventListener("click", async () => {
    try {
        const email = $("email").value.trim();
        const password = $("password").value;

        const data = await req("/api/staff/login", {
            method: "POST",
            body: {
                email,
                password
            }
        });

        st = data.token;

        $("login").classList.add("hide");
        $("console").classList.remove("hide");

        await Promise.all([
            overview(),
            events()
        ]);

        msg("Front Desk login successful.");

    } catch (error) {
        msg(error.message);
    }
});

// ==========================================
// FRONT DESK - OVERVIEW
// ==========================================

async function overview() {
    try {
        const data = await req(
            "/api/staff/overview",
            { auth: st }
        );

        $("metrics").innerHTML = `
            <article class="metric">

                <small>Total Orders</small>

                <h2>${escapeHTML(data.orders)}</h2>

            </article>

            <article class="metric">

                <small>Ready Reports</small>

                <h2>${escapeHTML(data.ready)}</h2>

            </article>

            <article class="metric">

                <small>Processing</small>

                <h2>${escapeHTML(data.processing)}</h2>

            </article>

            <article class="metric">

                <small>Open Callbacks</small>

                <h2>${escapeHTML(data.callbacks)}</h2>

            </article>
        `;

    } catch (error) {
        msg(error.message);
    }
}

// ==========================================
// FRONT DESK - PATIENT SEARCH
// ==========================================

$("search").addEventListener("click", searchPatients);

$("query").addEventListener("keydown", event => {
    if (event.key === "Enter") {
        searchPatients();
    }
});

async function searchPatients() {
    try {
        const query = $("query").value.trim();

        if (!query) {
            msg(
                "Enter a patient name, mobile or order reference."
            );
            return;
        }

        const data = await req(
            "/api/staff/search?q=" + encodeURIComponent(query),
            { auth: st }
        );

        if (!data.length) {
            $("matches").innerHTML =
                "<p>No matching records found.</p>";
            return;
        }

        $("matches").innerHTML = data.map(order => `
            <div class="order">

                <b>${escapeHTML(order.patient)}</b>

                <small>
                    ${escapeHTML(order.mobile)}
                    ·
                    ${escapeHTML(order.order_ref)}
                </small>

                <p>
                    ${escapeHTML(order.test_name)}
                    ·
                    ${escapeHTML(order.status)}
                </p>

                <button
                    type="button"
                    data-resend="${escapeHTML(order.order_ref)}">

                    Resend Report

                </button>

                <button
                    type="button"
                    data-staff-pdf="${escapeHTML(order.order_ref)}">

                    Download PDF

                </button>

            </div>
        `).join("");

        $("matches").querySelectorAll("[data-resend]").forEach(button => {
            button.addEventListener("click", () => {
                resend(button.dataset.resend);
            });
        });

        $("matches").querySelectorAll("[data-staff-pdf]").forEach(button => {
            button.addEventListener("click", () => {
                downloadStaffPdf(button.dataset.staffPdf);
            });
        });

    } catch (error) {
        msg(error.message);
    }
}

// ==========================================
// FRONT DESK - RESEND REPORT
// ==========================================

async function resend(ref) {
    try {
        const data = await req(
            `/api/staff/resend/${encodeURIComponent(ref)}`,
            {
                method: "POST",
                auth: st
            }
        );

        if (data.status === "SIMULATED" && data.url) {
            const fullUrl = new URL(data.url, window.location.origin).href;

            alert(
                `Report link generated successfully.

` +
                `Order: ${ref}
` +
                `Channel: Mock WhatsApp
` +
                `Status: ${data.status}
` +
                `Expires: ${data.expires_hours} hours
` +
                `OTP required on reopen: ${data.otp_required_on_reopen}

` +
                `Secure Link:
${fullUrl}`
            );
        } else {
            alert("Unexpected response: " + JSON.stringify(data));
        }

        await events();

    } catch (error) {
        alert("Resend failed: " + error.message);
    }
}

// ==========================================
// FRONT DESK - DOWNLOAD PDF
// ==========================================

async function downloadStaffPdf(ref) {
    try {
        const response = await fetch(
            `/api/staff/pdf/${encodeURIComponent(ref)}`,
            {
                headers: {
                    Authorization: "Bearer " + st
                }
            }
        );

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));

            throw new Error(
                error.detail || "PDF not found."
            );
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

        const link = document.createElement("a");

        link.href = url;
        link.download = ref + ".pdf";

        document.body.appendChild(link);
        link.click();
        link.remove();

        URL.revokeObjectURL(url);

        msg("PDF download started.");

    } catch (error) {
        msg(error.message);
    }
}

// ==========================================
// FRONT DESK - CSV IMPORT
// ==========================================

$("import").addEventListener("click", async () => {
    try {
        const file = $("csv").files[0];

        if (!file) {
            msg("Please select a CSV file.");
            return;
        }

        const formData = new FormData();

        formData.append("file", file);

        const data = await req(
            "/api/staff/import-csv",
            {
                method: "POST",
                auth: st,
                body: formData
            }
        );

        $("importMsg").textContent =
            `${data.imported} records imported successfully.`;

        msg("CSV import completed.");

        await overview();
        await events();

    } catch (error) {
        $("importMsg").textContent = error.message;
        msg(error.message);
    }
});

// ==========================================
// FRONT DESK - DELIVERY & ACCESS LOGS
// ==========================================

// Refresh button: refresh logs without reloading the page.

$("refresh").addEventListener("click", async () => {
    const button = $("refresh");

    if (!st) {
        msg("Please login to Front Desk first.");
        return;
    }

    button.disabled = true;
    button.textContent = "Refreshing...";

    try {
        const success = await events();

        if (success) {
            msg("System monitoring logs refreshed successfully.");
        }

    } catch (error) {
        msg("Failed to refresh logs: " + error.message);

    } finally {
        button.disabled = false;
        button.textContent = "↻ Refresh Logs";
    }
});

// Load delivery, access, callback and feedback events.

async function events() {
    try {
        if (!st) {
            throw new Error("Please login to Front Desk first.");
        }

        const data = await req(
            "/api/staff/events",
            { auth: st }
        );

        const delivery = data.delivery || [];
        const access = data.access || [];
        const callbacks = data.callbacks || [];
        const feedback = data.feedback || [];

        let feedbackHTML = "";

        if (feedback.length > 0) {
            feedbackHTML = feedback.map(item => {
                return `
                    <div class="order">

                        <div>

                            <b>${escapeHTML(item.ref)}</b>

                            <small>
                                Patient:
                                ${escapeHTML(item.patient_code)}
                                ·
                                ${escapeHTML(item.category)}
                            </small>

                            <p>
                                ${escapeHTML(
                                    item.comment || "No additional comments."
                                )}
                            </p>

                            <small>
                                Status:
                                ${escapeHTML(item.status)}
                                ·
                                ${escapeHTML(item.created_at || "")}
                            </small>

                        </div>

                    </div>
                `;
            }).join("");

        } else {
            feedbackHTML =
                "<p>No patient feedback received yet.</p>";
        }

        $("logs").innerHTML = `
            <h3>Delivery Events</h3>

            ${
                delivery.map(item => `
                    <div class="order">

                        <b>${escapeHTML(item.ref)}</b>

                        <small>
                            ${escapeHTML(item.status)}
                            ·
                            ${escapeHTML(item.destination)}
                        </small>

                    </div>
                `).join("")
                || "<p>No delivery events.</p>"
            }

            <h3>Access Events</h3>

            ${
                access.map(item => `
                    <div class="order">

                        <b>${escapeHTML(item.action)}</b>

                        <small>
                            ${escapeHTML(item.actor)}
                            ·
                            ${escapeHTML(item.ref)}
                        </small>

                    </div>
                `).join("")
                || "<p>No access events.</p>"
            }

            <h3>Open Callbacks</h3>

            ${
                callbacks.map(item => `
                    <div class="order">

                        <b>${escapeHTML(item.ref)}</b>

                        <small>
                            ${escapeHTML(item.reason)}
                        </small>

                    </div>
                `).join("")
                || "<p>No open callbacks.</p>"
            }

            <h3>Patient Summary Feedback</h3>

            ${feedbackHTML}
        `;

        return true;

    } catch (error) {
        msg(error.message);
        return false;
    }
}

// ==========================================
// ==========================================
// DOCTOR LOGIN AND REPORTS
// ==========================================

async function loadDoctorReports() {
    try {
        const data = await req("/api/doctor/reports", {
            auth: dt
        });

        $("doctorWelcome").textContent =
            data.doctor + " — Assigned Reports";

        $("doctorMetrics").innerHTML = `
            <div class="metric">
                <span>Reports in last 90 days</span>
                <b>${Number(data.count) || 0}</b>
            </div>
        `;

        if (!data.reports || data.reports.length === 0) {
            $("doctorReports").innerHTML =
                "<p>No signed reports found in the last 90 days.</p>";
            return;
        }

        $("doctorReports").innerHTML = data.reports.map(item => `
            <div class="order">
                <h3>
                    ${escapeHTML(item.order_ref)}
                    · ${escapeHTML(item.patient_name)}
                </h3>

                <p>
                    ${escapeHTML(item.patient_code)}
                    · ${escapeHTML(item.test_name)}
                </p>

                <p>
                    Status: ${escapeHTML(item.status)}
                    · Signed: ${escapeHTML(item.signed_at || "N/A")}
                </p>

                ${(item.results || []).map(value => `
                    <div class="order">
                        <b>${escapeHTML(value.analyte)}</b>

                        <p>
                            ${escapeHTML(String(value.value ?? ""))}
                            ${escapeHTML(value.unit || "")}
                        </p>

                        <small>
                            Reference: ${escapeHTML(value.reference_range || "N/A")}
                            · Flag: ${escapeHTML(value.flag || "NORMAL")}
                            ${value.critical ? " · CRITICAL" : ""}
                        </small>
                    </div>
                `).join("")}
            </div>
        `).join("");

    } catch (error) {
        msg(error.message);
    }
}

$("doctorSignin").addEventListener("click", async () => {
    const button = $("doctorSignin");

    try {
        button.disabled = true;

        const data = await req("/api/doctor/login", {
            method: "POST",
            body: {
                doctor_name: $("doctorName").value,
                password: $("doctorPassword").value
            }
        });

        dt = data.token;

        $("doctorLogin").classList.add("hide");
        $("doctorConsole").classList.remove("hide");
        $("doctorPassword").value = "";

        await loadDoctorReports();

    } catch (error) {
        msg(error.message);
    } finally {
        button.disabled = false;
    }
});

$("doctorRefresh").addEventListener("click", loadDoctorReports);
// ==========================================
// PATHOLOGIST LOGIN AND SUMMARY REVIEWS
// ==========================================

let pathologistToken = null;

async function loadPathologistReviews() {
    try {
        const data = await req("/api/pathologist/reviews", {
            auth: pathologistToken
        });

        const reviewed = Number(data.reviewed_this_week) || 0;
        const target = Number(data.weekly_target) || 50;
        const pending = (data.reviews || []).length;

        $("pathologistMetrics").innerHTML = `
            <div class="metric">
                <span>Pending Reviews</span>
                <b>${pending}</b>
            </div>
            <div class="metric">
                <span>Reviewed This Week</span>
                <b>${reviewed} / ${target}</b>
            </div>
        `;

        if (!pending) {
            $("pathologistReviews").innerHTML =
                "<p>No pending summaries available.</p>";
            return;
        }

        $("pathologistReviews").innerHTML = data.reviews.map((item, index) => `
            <div class="order" data-review-card>
                <h3>
                    ${escapeHTML(item.order_ref)}
                    · ${escapeHTML(item.patient_name)}
                </h3>

                <p>
                    ${escapeHTML(item.test_name)}
                    · Source: ${escapeHTML(item.summary_source)}
                </p>

                <p><b>Summary for review</b></p>
                <p>${escapeHTML(item.summary_text)}</p>

                <small>
                    Created: ${escapeHTML(item.created_at || "N/A")}
                    · Status: ${escapeHTML(item.status)}
                </small>

                <label for="pathologistNote${index}">Decision note</label>
                <textarea
                    id="pathologistNote${index}"
                    data-review-note
                    rows="3"
                    placeholder="Enter review comments (optional)"
                ></textarea>

                <div class="row">
                    <button
                        type="button"
                        data-review-decision="APPROVED"
                        data-review-ref="${escapeHTML(item.order_ref)}"
                    >Approve</button>

                    <button
                        type="button"
                        data-review-decision="REJECTED"
                        data-review-ref="${escapeHTML(item.order_ref)}"
                    >Reject</button>
                </div>
            </div>
        `).join("");

    } catch (error) {
        msg(error.message);
    }
}

$("pathologistSignin").addEventListener("click", async () => {
    const button = $("pathologistSignin");

    try {
        button.disabled = true;

        const data = await req("/api/pathologist/login", {
            method: "POST",
            body: {
                name: $("pathologistName").value.trim(),
                password: $("pathologistPassword").value
            }
        });

        pathologistToken = data.token;

        $("pathologistLogin").classList.add("hide");
        $("pathologistConsole").classList.remove("hide");
        $("pathologistPassword").value = "";

        await loadPathologistReviews();

    } catch (error) {
        msg(error.message);
    } finally {
        button.disabled = false;
    }
});

$("pathologistRefresh").addEventListener(
    "click",
    loadPathologistReviews
);

$("pathologistReviews").addEventListener("click", async event => {
    const button = event.target.closest("[data-review-decision]");

    if (!button) return;

    const ref = button.dataset.reviewRef;
    const decision = button.dataset.reviewDecision;
    const card = button.closest("[data-review-card]");
    const note = card.querySelector("[data-review-note]").value;

    try {
        button.disabled = true;

        await req(
            "/api/pathologist/reviews/" +
            encodeURIComponent(ref) +
            "/decision",
            {
                method: "POST",
                auth: pathologistToken,
                body: {
                    decision: decision,
                    note: note
                }
            }
        );

        msg("Review " + decision.toLowerCase() + " successfully.");
        await loadPathologistReviews();

    } catch (error) {
        msg(error.message);
    } finally {
        button.disabled = false;
    }
});

// GLOBAL FUNCTIONS
// ==========================================

window.report = report;
window.downloadPatientPdf = downloadPatientPdf;
window.orders = orders;
window.secure = secure;
window.resend = resend;
window.downloadStaffPdf = downloadStaffPdf;
window.submitFeedback = submitFeedback;

console.log(
    "LABFLOW application JavaScript loaded successfully."
);


















// ==========================================
// NAVIGATION FIX - EVENT DELEGATION
// ==========================================

document.addEventListener("click", function(event) {
    const button = event.target.closest('nav button[data-tab]');

    if (!button) return;

    const target = button.dataset.tab;
    const sections = ["patient", "staff", "doctor", "pathologist"];

    sections.forEach(id => {
        const section = document.getElementById(id);
        if (section) {
            section.classList.toggle("hide", id !== target);
        }
    });

    document.querySelectorAll("nav button[data-tab]").forEach(btn => {
        btn.classList.toggle("active", btn === button);
    });

    console.log("LABFLOW NAVIGATION:", target);
});
// ==========================================
// LABFLOW - CRITICAL BUTTON EVENT FALLBACK
// ==========================================

document.addEventListener("click", async function (event) {

    const button = event.target.closest("button");
    if (!button) return;

    const handlers = {

        send: async () => {
            const mobile = $("mobile").value.trim();

            if (!/^\d{10,}$/.test(mobile)) {
                alert("Please enter a valid mobile number.");
                return;
            }

            button.disabled = true;

            try {
                await req("/api/patient/request-otp", {
                    method: "POST",
                    body: { mobile }
                });

                alert("Demo OTP generated. Check VS Code terminal.");

            } finally {
                button.disabled = false;
            }
        },

        verify: async () => {
            const mobile = $("mobile").value.trim();
            const otp = $("otp").value.trim();

            if (!/^\d{6}$/.test(otp)) {
                msg("Enter the 6-digit OTP.");
                return;
            }

            button.disabled = true;

            try {
                const data = await req("/api/patient/verify-otp", {
                    method: "POST",
                    body: { mobile, otp }
                });

                pt = data.token;
                await showPatientProfiles(data.profiles || []);

                msg("OTP verified successfully.");

            } finally {
                button.disabled = false;
            }
        },

        signin: async () => {
            button.disabled = true;

            try {
                const data = await req("/api/staff/login", {
                    method: "POST",
                    body: {
                        email: $("email").value.trim(),
                        password: $("password").value
                    }
                });

                st = data.token;

                $("login").classList.add("hide");
                $("console").classList.remove("hide");

                await Promise.all([overview(), events()]);

                msg("Front Desk login successful.");

            } finally {
                button.disabled = false;
            }
        },

        doctorSignin: async () => {
            button.disabled = true;

            try {
                const data = await req("/api/doctor/login", {
                    method: "POST",
                    body: {
                        doctor_name: $("doctorName").value,
                        password: $("doctorPassword").value
                    }
                });

                dt = data.token;

                $("doctorLogin").classList.add("hide");
                $("doctorConsole").classList.remove("hide");
                $("doctorPassword").value = "";

                await loadDoctorReports();

            } finally {
                button.disabled = false;
            }
        },

        pathologistSignin: async () => {
            button.disabled = true;

            try {
                const data = await req("/api/pathologist/login", {
                    method: "POST",
                    body: {
                        name: $("pathologistName").value.trim(),
                        password: $("pathologistPassword").value
                    }
                });

                pathologistToken = data.token;

                $("pathologistLogin").classList.add("hide");
                $("pathologistConsole").classList.remove("hide");
                $("pathologistPassword").value = "";

                await loadPathologistReviews();

            } finally {
                button.disabled = false;
            }
        }

    };

    if (!handlers[button.id]) return;

    event.preventDefault();
    event.stopImmediatePropagation();

    try {
        await handlers[button.id]();
    } catch (error) {
        console.error("LABFLOW BUTTON ERROR:", error);
        alert(error.message || "Something went wrong.");
    }

}, true);

console.log("LABFLOW critical button fallback initialized.");
