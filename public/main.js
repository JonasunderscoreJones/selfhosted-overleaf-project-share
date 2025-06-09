const projectId = window.location.pathname.split("/")[2];
const base = `/projects/${projectId}`;
const fileListEl = document.getElementById("file-list");
const codeEl = document.getElementById("code");
const pdfEl = document.getElementById("pdf");
const pdfErrorEl = document.getElementById("pdf-error");

const sidebarEl = document.querySelector(".sidebar");
const editorEl = document.querySelector(".editor");
const previewContainerEl = document.querySelector(".preview-container");
const dragbar = document.getElementById("dragbar");
const mainEl = document.querySelector("main");

document.getElementById("open-in-editor-button").onclick = () => {
    window.open(`https://tex.jonasjones.dev/project/${projectId}`, "_blank");
};

// Set project ID in header
document.getElementById("project-id").textContent = projectId;

async function listFiles() {
    try {
    const res = await fetch(`${base}/`);
    if (!res.ok) throw new Error("Failed to fetch file list");
    const text = await res.text();
    const parser = new DOMParser();
    const doc = parser.parseFromString(text, "text/html");
    const links = Array.from(doc.querySelectorAll("a"));

    const sourceFiles = [];
    let pdfFiles = [];

    for (const link of links) {
        const name = link.getAttribute("href");
        if (!name) continue;
        if (name === '../' || name.endsWith('/')) continue;
        if (/\.(tex|bib|cls|sty|txt)$/i.test(name)) {
        sourceFiles.push(name);
        } else if (name.toLowerCase().endsWith(".pdf")) {
        pdfFiles.push(name);
        }
    }

    if (sourceFiles.length === 0) {
        codeEl.textContent = "// No source files found.";
    }

    // Add files to sidebar WITHOUT numbering
    sourceFiles.forEach((file, idx) => {
        const li = document.createElement("li");
        li.textContent = file;
        if (idx === 0) li.classList.add("active");
        li.onclick = () => {
        document.querySelectorAll(".sidebar li").forEach(el => el.classList.remove("active"));
        li.classList.add("active");
        loadSourceFile(file);
        };
        fileListEl.appendChild(li);
    });

    if (sourceFiles.length > 0) {
        loadSourceFile(sourceFiles[0]);
    }

    // PDF fallback: output.pdf > main.pdf > any .pdf
    let pdfToLoad = pdfFiles.find(f => f.toLowerCase() === "output.pdf")
                    || pdfFiles.find(f => f.toLowerCase() === "main.pdf")
                    || pdfFiles[0];

    if (pdfToLoad) {
        loadPDF(pdfToLoad);
        document.getElementById("download-pdf-button").href = pdfToLoad;
    } else {
        showPDFError(true);
        document.getElementById("download-pdf-button").style.display = "none";
    }

    } catch (err) {
    codeEl.textContent = `// Error loading file list: ${err.message}`;
    showPDFError(true);
    }
}

async function loadSourceFile(file) {
    try {
    const res = await fetch(`${base}/${file}`);
    if (!res.ok) throw new Error("Failed to load file");
    const content = await res.text();

    codeEl.textContent = content;

    // Change prism language class based on file extension
    const ext = file.split('.').pop().toLowerCase();
    codeEl.className = `language-${ext === "tex" ? "latex" : ext}`;
    Prism.highlightElement(codeEl);
    } catch (err) {
    codeEl.textContent = `// Error loading file: ${err.message}`;
    }
}

function loadPDF(pdfFile) {
    showPDFError(false);
    pdfEl.src = `${base}/${pdfFile}`;
}

function showPDFError(show) {
    pdfErrorEl.style.display = show ? "block" : "none";
    if (show) {
    pdfEl.style.display = "none";
    } else {
    pdfEl.style.display = "block";
    }
}

pdfEl.onerror = () => {
    showPDFError(true);
};

pdfEl.onload = () => {
    showPDFError(false);
};

// Draggable vertical separator
let isDragging = false;

dragbar.addEventListener("mousedown", e => {
    isDragging = true;
    document.body.style.cursor = "ew-resize";
    e.preventDefault();
});

window.addEventListener("mouseup", e => {
    if (isDragging) {
    isDragging = false;
    document.body.style.cursor = "";
    }
});

window.addEventListener("mousemove", e => {
    if (!isDragging) return;

    const containerRect = mainEl.getBoundingClientRect();

    const sidebarWidth = sidebarEl.offsetWidth;
    const availableWidth = containerRect.width - sidebarWidth - dragbar.offsetWidth;

    let newEditorWidth = e.clientX - containerRect.left - sidebarWidth;
    newEditorWidth = Math.max(200, Math.min(newEditorWidth, availableWidth - 200));

    if (availableWidth - newEditorWidth < 415) {
    newEditorWidth = availableWidth - 415;
    }

    editorEl.style.flex = "none";
    previewContainerEl.style.flex = "none";

    editorEl.style.width = newEditorWidth + "px";
    previewContainerEl.style.width = (availableWidth - newEditorWidth) + "px";
});

listFiles();