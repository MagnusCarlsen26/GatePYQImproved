const tableBody = document.getElementById('tableBody');
const subjectFilter = document.getElementById('subjectFilter');
const searchInput = document.getElementById('searchInput');
const statsDisplay = document.getElementById('statsDisplay');

let allQuestions = [];

document.addEventListener('DOMContentLoaded', () => {
    fetchData();
});

async function fetchData() {
    try {
        const response = await fetch('../extraction/questions.json');
        if (!response.ok) {
            throw new Error("JSON not found");
        }
        const rawData = await response.json();

        // Flatten the nested structure for the viewer
        allQuestions = [];
        // Iterate over Subjects
        Object.values(rawData).forEach(subjectTests => {
            // Iterate over Tests in Subject
            subjectTests.forEach(test => {
                // Iterate over Sections in Test
                if (test.sections) {
                    test.sections.forEach(section => {
                        if (section.questions) {
                            allQuestions.push(...section.questions);
                        }
                    });
                }
            });
        });

        // Initialize View
        renderQuestions(allQuestions);
        updateStats(allQuestions);

        // Initialize Review Table Filters
        initializeReviewFilters();
        renderReviewTable(allQuestions);

    } catch (error) {
        console.error("Could not fetch JSON", error);
        document.getElementById('questions-container').innerHTML =
            `<div class="error">Failed to load data. Please ensure you are running a server and 'extraction/questions.json' exists. URL attempted: ../extraction/questions.json</div>`;
    }
}

// --- View Switching ---
window.switchView = function (viewName) {
    // Update Tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
        if (tab.textContent.includes(viewName === 'viewer' ? 'Viewer' : 'Review')) {
            tab.classList.add('active');
        }
    });

    // Update Sections
    document.querySelectorAll('.view-section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(`${viewName}-section`).classList.add('active');
}

// --- Viewer Logic ---
function renderQuestions(questions) {
    const container = document.getElementById('questions-container');
    container.innerHTML = '';

    questions.forEach((q, index) => {
        const card = document.createElement('div');
        card.className = 'question-card tex2jax_process';
        card.id = `q-${q.post_id}`; // Changed to match metadata key

        // Handle tags (can be array or string)
        let tagsHtml = '';
        if (q.tags && Array.isArray(q.tags)) {
            tagsHtml = q.tags.map(tag => `<span class="tag">${tag}</span>`).join('');
        }

        // Handle Options (metadata might not have options, handle gracefully)
        let optionsHtml = '';
        if (q.options) {
            optionsHtml = Object.entries(q.options).map(([label, text]) => `
                <div class="option-item">
                    <span class="option-label">${label}</span>
                    <div class="option-content">${text}</div>
                </div>
            `).join('');
        }

        // Determine content to display (Metadata might just have title, full questions have 'question')
        const content = q.question || `<h3>${q.title}</h3><p>(Full question content not available in metadata view)</p>`;

        card.innerHTML = `
            <div class="card-header">
                <div class="meta-row">
                    <span class="qid">#${q.post_id}</span>
                    <span class="year-badge">${q.year || 'Year ???'}</span>
                    <span class="subject-badge">${q.subject || 'Subject ???'}</span>
                    ${q.question_num ? `<span class="qnum-badge">Q.${q.question_num}</span>` : ''}
                </div>
                <div class="meta-row-title">
                     <strong>${q.title || ''}</strong>
                </div>
                <div class="tags">
                    ${q.subtopic ? `<span class="subtopic-tag">${q.subtopic}</span>` : ''}
                    ${tagsHtml}
                </div>
            </div>
            <div class="question-text">
                ${content}
            </div>
            <div class="options-container">
                ${optionsHtml}
            </div>
            <div class="action-buttons">
                <button class="btn btn-primary toggle-solution" data-id="${q.post_id}">View Solution</button>
            </div>
            <div class="solution-panel" id="sol-${q.post_id}">
                <div class="answer-badge">Correct Answer: ${q.answer || 'N/A'}</div>
                <div class="solution-content">
                    ${q.solution || 'No solution available.'}
                </div>
            </div>
        `;

        container.appendChild(card);
    });

    attachEventListeners();

    if (window.MathJax && window.MathJax.typeset) {
        window.MathJax.typeset();
    }
}

function updateStats(questions) {
    const total = questions.length;
    const subjects = new Set();
    questions.forEach(q => {
        if (q.subject) subjects.add(q.subject);
    });

    document.getElementById('stats-bar').innerHTML = `
        <span><strong>${total}</strong> Questions</span>
        <span><strong>${subjects.size}</strong> Subjects</span>
    `;
}

function attachEventListeners() {
    document.querySelectorAll('.toggle-solution').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const id = e.target.getAttribute('data-id');
            const panel = document.getElementById(`sol-${id}`);
            if (panel) {
                const isOpen = panel.classList.toggle('open');
                e.target.textContent = isOpen ? 'Hide Solution' : 'View Solution';
            }
        });
    });
}

// --- Review Table Logic ---
function initializeReviewFilters() {
    const subjects = new Set(allQuestions.map(item => item.subject));
    [...subjects].sort().forEach(sub => {
        const option = document.createElement('option');
        option.value = sub;
        option.textContent = sub;
        // Check if exists to avoid duplicates if re-initialized
        if (![...subjectFilter.options].some(o => o.value === sub)) {
            subjectFilter.appendChild(option);
        }
    });

    subjectFilter.addEventListener('change', filterReviewData);
    searchInput.addEventListener('input', filterReviewData);
}

function renderReviewTable(dataToRender) {
    tableBody.innerHTML = '';
    dataToRender.forEach(item => {
        const row = document.createElement('tr');
        const subtopicHtml = item.subtopic ? `<span class="tag">${item.subtopic}</span>` : '';

        row.innerHTML = `
            <td><a href="../scraped_html/cleaned/${item.post_id}.html" class="link" target="_blank">${item.post_id}</a></td>
            <td>${item.year || '-'}</td>
            <td>${item.question_num || '-'}</td>
            <td>${item.subject || 'Other'}</td>
            <td>${subtopicHtml}</td>
            <td><small>${item.title}</small></td>
        `;
        tableBody.appendChild(row);
    });
    statsDisplay.textContent = `Showing ${dataToRender.length} of ${allQuestions.length} questions`;
}

function filterReviewData() {
    const subject = subjectFilter.value;
    const search = searchInput.value.toLowerCase();

    const filtered = allQuestions.filter(item => {
        const matchesSubject = subject === 'All' || item.subject === subject;
        const matchesSearch = (item.title || '').toLowerCase().includes(search) ||
            (item.post_id || '').includes(search);
        return matchesSubject && matchesSearch;
    });

    renderReviewTable(filtered);
}
