document.addEventListener('DOMContentLoaded', () => {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const results = document.getElementById('results');
    const intensity = document.getElementById('intensity');
    const intensityVal = document.getElementById('intensityVal');
    const status = document.getElementById('status');
    const originalImg = document.getElementById('originalImg');
    const processedImg = document.getElementById('processedImg');
    const scoresContainer = document.getElementById('scoresContainer');
    const resetBtn = document.getElementById('resetBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const summaryInfo = document.getElementById('summaryInfo');
    const blurLabel = document.getElementById('blurLabel');
    const skeleton = document.getElementById('skeleton');
    const blurOverlay = document.getElementById('blurOverlay');
    const batchPanel = document.getElementById('batchPanel');
    const queueCount = document.getElementById('queueCount');
    const apiKeyInput = document.getElementById('apiKeyInput');

    const DEFAULT_KEY = 'NSFW_PRO_8rqNo38SzYgZX86-byPnlZvvXzpiJL5rbE_TYIkbce8';
    const OLD_DEFAULT = 'pro_guard_secret_2024';

    // Safety: Clear old insecure key if it exists in storage
    if (localStorage.getItem('nsfw_api_key') === OLD_DEFAULT) {
        localStorage.removeItem('nsfw_api_key');
    }

    // Load saved key
    if (localStorage.getItem('nsfw_api_key')) {
        apiKeyInput.value = localStorage.getItem('nsfw_api_key');
    } else {
        apiKeyInput.value = DEFAULT_KEY;
    }

    apiKeyInput.addEventListener('change', (e) => {
        localStorage.setItem('nsfw_api_key', e.target.value);
    });

    let allResults = [];

    const colorPickerContainer = document.getElementById('colorPickerContainer');
    const solidColor = document.getElementById('solidColor');

    document.querySelectorAll('input[name="mode"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            if (e.target.value === 'solid') {
                colorPickerContainer.classList.remove('hidden');
            } else {
                colorPickerContainer.classList.add('hidden');
            }
        });
    });

    intensity.addEventListener('input', (e) => {
        intensityVal.textContent = e.target.value;
    });

    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('border-blue-500', 'bg-blue-500/5');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('border-blue-500', 'bg-blue-500/5');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('border-blue-500', 'bg-blue-500/5');
        handleUpload(e.dataTransfer.files);
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) handleUpload(e.target.files);
    });

    const handleUpload = async (files) => {
        if (!files || files.length === 0) return;

        allResults = [];
        queueList.innerHTML = '';
        batchPanel.classList.remove('hidden');
        results.classList.add('hidden');
        queueCount.textContent = `${files.length} Files`;

        for (let i = 0; i < files.length; i++) {
            const item = document.createElement('div');
            item.className = "flex-shrink-0 w-24 h-24 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center relative overflow-hidden group cursor-pointer transition hover:border-blue-500";
            item.innerHTML = `<div class="spinner scale-50"></div><span class="text-[10px] text-slate-500 absolute bottom-1">Pending</span>`;
            item.id = `queue-item-${i}`;
            queueList.appendChild(item);
        }

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const itemEl = document.getElementById(`queue-item-${i}`);
            itemEl.innerHTML = `<div class="spinner scale-50"></div><span class="text-[10px] text-blue-400 absolute bottom-1">Processing</span>`;

            const formData = new FormData();
            formData.append('file', file);
            formData.append('mode', document.querySelector('input[name="mode"]:checked').value);
            formData.append('intensity', intensity.value);
            formData.append('color', solidColor.value);

            const userKey = apiKeyInput.value.trim() || DEFAULT_KEY;

            try {
                const response = await fetch('/api/process', {
                    method: 'POST',
                    headers: { 'X-API-KEY': userKey },
                    body: formData
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Upload failed');
                }

                const data = await response.json();

                itemEl.innerHTML = `<img src="${data.processed_url}" class="w-full h-full object-cover">`;
                itemEl.onclick = () => displayResult(data, file);

                allResults.push({ data, file });
                if (i === 0) displayResult(data, file);

            } catch (err) {
                itemEl.innerHTML = `<span class="text-red-500 text-[10px]">Error</span>`;
            }
        }
    };

    const displayResult = (data, originalFile) => {
        results.classList.remove('hidden');
        results.scrollIntoView({ behavior: 'smooth' });
        fileNameDisplay.textContent = originalFile.name;
        status.innerHTML = `<svg class="h-4 w-4 text-green-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg> Analysis Complete`;

        const reader = new FileReader();
        reader.onload = (e) => originalImg.src = e.target.result;
        reader.readAsDataURL(originalFile);

        skeleton.classList.remove('hidden');
        processedImg.classList.add('opacity-0');
        blurOverlay.classList.add('opacity-0');

        const img = new Image();
        img.onload = () => {
            processedImg.src = img.src;
            processedImg.classList.remove('opacity-0');
            processedImg.classList.add('opacity-100');
            skeleton.classList.add('hidden');
            if (data.blur_count > 0) {
                blurOverlay.classList.remove('opacity-0');
                blurOverlay.classList.add('opacity-100');
            }
        };
        img.src = data.processed_url;
        downloadBtn.href = data.processed_url;

        renderScores(data.scores);

        blurLabel.textContent = data.blur_count > 0 ? "CENSORED" : "CLEAN";
        blurLabel.className = data.blur_count > 0 ?
            "text-[10px] bg-red-600 text-white px-2 py-0.5 rounded-full font-bold uppercase" :
            "text-[10px] bg-green-600 text-white px-2 py-0.5 rounded-full font-bold uppercase";

        if (data.blur_count > 0) {
            summaryInfo.innerHTML = `Identified <span class="text-white font-bold">${data.detections.length}</span> objects. Applied <span class="text-blue-400 font-bold">${data.blur_count}</span> selective blocks.`;
        } else {
            summaryInfo.innerHTML = "No highly sensitive areas detected. The image appears safe.";
        }
    };

    function renderScores(scores) {
        scoresContainer.innerHTML = '';
        if (!scores || scores.length === 0) return;

        scores.sort((a, b) => b.score - a.score);
        scores.forEach(s => {
            const pct = (s.score * 100).toFixed(1);
            const colorClass = getScoreColor(s.label);
            const item = document.createElement('div');
            item.className = 'space-y-1.5';
            item.innerHTML = `
                <div class="flex justify-between text-xs items-center">
                    <span class="font-bold tracking-wide uppercase">${s.label}</span>
                    <span class="text-slate-400 font-medium">${pct}%</span>
                </div>
                <div class="score-bar">
                    <div class="score-fill ${colorClass}" style="width: ${pct}%"></div>
                </div>
            `;
            scoresContainer.appendChild(item);
        });
    }

    function getScoreColor(label) {
        label = label.toLowerCase();
        if (label === 'neutral' || label === 'drawings') return 'bg-green-500';
        if (label === 'sexy') return 'bg-yellow-500';
        if (label === 'porn' || label === 'hentai') return 'bg-red-500';
        return 'bg-blue-500';
    }

    resetBtn.addEventListener('click', () => {
        results.classList.add('hidden');
        batchPanel.classList.add('hidden');
        fileInput.value = '';
        originalImg.src = '';
        processedImg.src = '';
        fileNameDisplay.textContent = '';
        summaryInfo.innerHTML = '';
        allResults = [];
        queueList.innerHTML = '';
        status.innerHTML = '<div class="spinner"></div> Ready';
    });
});
