class EducationPlayer {
    constructor() {
        this.presentation = null;
        this.currentTopicIndex = 0;
        this.isPlaying = false;
        this.devMode = false;
        this.audio = new Audio();
        
        this.initElements();
        this.initEventListeners();
        this.checkExistingPresentation();
    }
    
    initElements() {
        this.mainVideo = document.getElementById('mainVideo');
        this.playBtn = document.getElementById('playBtn');
        this.progressBar = document.getElementById('progressBar');
        this.progressContainer = document.getElementById('progressContainer');
        this.timeDisplay = document.getElementById('timeDisplay');
        this.volumeSlider = document.getElementById('volumeSlider');
        this.subtitles = document.getElementById('subtitles');
        this.topicTitle = document.getElementById('topicTitle');
        this.topicMeta = document.getElementById('topicMeta');
        this.topicList = document.getElementById('topicList');
        this.contentZone = document.getElementById('contentZone');
        this.avatarZone = document.getElementById('avatarZone');
        this.devModeToggle = document.getElementById('devModeToggle');
        this.devPanel = document.getElementById('devPanel');
        this.uploadSection = document.getElementById('uploadSection');
        this.mainContent = document.getElementById('mainContent');
    }
    
    initEventListeners() {
        this.playBtn.addEventListener('click', () => this.togglePlay());
        this.mainVideo.addEventListener('timeupdate', () => this.updateProgress());
        this.mainVideo.addEventListener('ended', () => this.onVideoEnded());
        this.progressContainer.addEventListener('click', (e) => this.seek(e));
        this.volumeSlider.addEventListener('input', (e) => this.setVolume(e.target.value));
        this.devModeToggle.addEventListener('click', () => this.toggleDevMode());
        
        document.getElementById('fileInput').addEventListener('change', (e) => this.handleFileUpload(e));
        
        document.getElementById('devContentWidth').addEventListener('input', (e) => this.updateDevLayout());
        document.getElementById('devAvatarScale').addEventListener('input', (e) => this.updateDevLayout());
        document.getElementById('devContentPosition').addEventListener('change', (e) => this.updateDevLayout());
        document.getElementById('devAvatarMode').addEventListener('change', (e) => this.updateDevLayout());
        
        this.audio.addEventListener('timeupdate', () => this.updateSubtitles());
    }
    
    async checkExistingPresentation() {
        try {
            const response = await fetch('/player/assets/presentation.json');
            if (response.ok) {
                this.presentation = await response.json();
                this.showPlayer();
                this.renderTopicList();
                if (this.presentation.topics && this.presentation.topics.length > 0) {
                    this.loadTopic(0);
                }
            }
        } catch (e) {
            console.log('No existing presentation found');
        }
    }
    
    showPlayer() {
        this.uploadSection.style.display = 'none';
        this.mainContent.style.display = 'grid';
    }
    
    async handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('subject', document.getElementById('subjectSelect').value);
        formData.append('grade', document.getElementById('gradeSelect').value);
        
        this.showLoading();
        
        try {
            const response = await fetch('/process_pdf', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.status === 'completed') {
                await this.checkExistingPresentation();
            } else {
                alert('Processing failed: ' + (result.error || 'Unknown error'));
            }
        } catch (e) {
            alert('Upload failed: ' + e.message);
        }
    }
    
    showLoading() {
        this.uploadSection.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <p>Processing your content...</p>
                <p style="color: #aaa; font-size: 0.9rem;">This may take a few minutes</p>
            </div>
        `;
    }
    
    renderTopicList() {
        if (!this.presentation || !this.presentation.topics) {
            this.topicList.innerHTML = '<div class="no-content">No topics available</div>';
            return;
        }
        
        this.topicList.innerHTML = this.presentation.topics.map((topic, index) => `
            <div class="topic-item ${index === this.currentTopicIndex ? 'active' : ''}" 
                 data-index="${index}" 
                 onclick="player.loadTopic(${index})">
                <div class="topic-thumb">Topic ${topic.id}</div>
                <div class="topic-details">
                    <h4>${topic.title}</h4>
                    <div class="duration">${topic.duration || 30}s | ${topic.renderer}</div>
                </div>
            </div>
        `).join('');
    }
    
    loadTopic(index) {
        if (!this.presentation || !this.presentation.topics[index]) return;
        
        this.currentTopicIndex = index;
        const topic = this.presentation.topics[index];
        
        this.topicTitle.textContent = topic.title;
        this.topicMeta.textContent = `${this.presentation.subject} | Grade ${this.presentation.grade} | ${topic.renderer}`;
        
        this.mainVideo.src = `/player/assets/videos/topic_${topic.id}.mp4`;
        this.audio.src = `/player/assets/audio/topic_${topic.id}.mp3`;
        
        this.applyLayout(topic.layout);
        
        document.querySelectorAll('.topic-item').forEach((el, i) => {
            el.classList.toggle('active', i === index);
        });
        
        this.isPlaying = false;
        this.playBtn.innerHTML = '&#9658;';
        this.progressBar.style.width = '0%';
        this.subtitles.classList.remove('visible');
    }
    
    applyLayout(layout) {
        if (!layout) {
            layout = {
                content_zone: { position: 'left', width_percent: 65 },
                avatar_zone: { mode: 'side', position: 'right', width_percent: 35, scale: 0.35 }
            };
        }
        
        const contentWidth = layout.content_zone?.width_percent || 65;
        const avatarWidth = layout.avatar_zone?.width_percent || 35;
        const contentPos = layout.content_zone?.position || 'left';
        const avatarMode = layout.avatar_zone?.mode || 'side';
        const avatarScale = layout.avatar_zone?.scale || 0.35;
        
        this.contentZone.style.width = `${contentWidth}%`;
        this.contentZone.style.height = '100%';
        
        if (contentPos === 'left') {
            this.contentZone.style.left = '0';
            this.contentZone.style.right = 'auto';
        } else {
            this.contentZone.style.right = '0';
            this.contentZone.style.left = 'auto';
        }
        
        if (avatarMode === 'overlay') {
            this.avatarZone.style.width = `${avatarScale * 100}%`;
            this.avatarZone.style.height = 'auto';
            this.avatarZone.style.aspectRatio = '1';
            this.avatarZone.style.bottom = '80px';
            this.avatarZone.style.right = '20px';
            this.avatarZone.style.top = 'auto';
            this.avatarZone.style.left = 'auto';
        } else {
            this.avatarZone.style.width = `${avatarWidth}%`;
            this.avatarZone.style.height = '100%';
            this.avatarZone.style.top = '0';
            
            if (contentPos === 'left') {
                this.avatarZone.style.right = '0';
                this.avatarZone.style.left = 'auto';
            } else {
                this.avatarZone.style.left = '0';
                this.avatarZone.style.right = 'auto';
            }
        }
    }
    
    togglePlay() {
        if (this.isPlaying) {
            this.pause();
        } else {
            this.play();
        }
    }
    
    play() {
        this.mainVideo.play();
        this.audio.play();
        this.isPlaying = true;
        this.playBtn.innerHTML = '&#10074;&#10074;';
    }
    
    pause() {
        this.mainVideo.pause();
        this.audio.pause();
        this.isPlaying = false;
        this.playBtn.innerHTML = '&#9658;';
    }
    
    updateProgress() {
        const duration = this.mainVideo.duration || 0;
        const currentTime = this.mainVideo.currentTime || 0;
        const progress = (currentTime / duration) * 100;
        
        this.progressBar.style.width = `${progress}%`;
        this.timeDisplay.textContent = `${this.formatTime(currentTime)} / ${this.formatTime(duration)}`;
        
        if (Math.abs(this.audio.currentTime - currentTime) > 0.3) {
            this.audio.currentTime = currentTime;
        }
    }
    
    formatTime(seconds) {
        if (isNaN(seconds)) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
    
    seek(event) {
        const rect = this.progressContainer.getBoundingClientRect();
        const pos = (event.clientX - rect.left) / rect.width;
        const newTime = pos * this.mainVideo.duration;
        
        this.mainVideo.currentTime = newTime;
        this.audio.currentTime = newTime;
    }
    
    setVolume(value) {
        this.mainVideo.volume = value;
        this.audio.volume = value;
    }
    
    updateSubtitles() {
        if (!this.presentation || !this.presentation.topics[this.currentTopicIndex]) return;
        
        const topic = this.presentation.topics[this.currentTopicIndex];
        const segments = topic.segments || [];
        const currentTime = this.audio.currentTime;
        
        let currentSegment = null;
        for (const segment of segments) {
            const start = segment.start;
            const end = start + segment.duration;
            if (currentTime >= start && currentTime < end) {
                currentSegment = segment;
                break;
            }
        }
        
        if (currentSegment) {
            this.subtitles.textContent = currentSegment.text;
            this.subtitles.classList.add('visible');
        } else {
            this.subtitles.classList.remove('visible');
        }
    }
    
    onVideoEnded() {
        this.isPlaying = false;
        this.playBtn.innerHTML = '&#9658;';
        
        if (this.currentTopicIndex < this.presentation.topics.length - 1) {
            setTimeout(() => this.loadTopic(this.currentTopicIndex + 1), 1000);
        }
    }
    
    toggleDevMode() {
        this.devMode = !this.devMode;
        this.devModeToggle.classList.toggle('active', this.devMode);
        this.devPanel.classList.toggle('visible', this.devMode);
    }
    
    updateDevLayout() {
        if (!this.devMode) return;
        
        const contentWidth = document.getElementById('devContentWidth').value;
        const avatarScale = document.getElementById('devAvatarScale').value;
        const contentPosition = document.getElementById('devContentPosition').value;
        const avatarMode = document.getElementById('devAvatarMode').value;
        
        this.applyLayout({
            content_zone: { position: contentPosition, width_percent: parseInt(contentWidth) },
            avatar_zone: { mode: avatarMode, position: contentPosition === 'left' ? 'right' : 'left', width_percent: 100 - parseInt(contentWidth), scale: parseFloat(avatarScale) }
        });
    }
}

function useSampleContent() {
    const sampleMarkdown = `# Introduction to Photosynthesis

## What is Photosynthesis?
Photosynthesis is the process by which green plants and some other organisms use sunlight to synthesize foods from carbon dioxide and water.

## The Process
Plants absorb carbon dioxide from the air through tiny pores called stomata. Water is absorbed by roots from the soil. Using the energy from sunlight captured by chlorophyll, plants convert these into glucose and oxygen.

## The Equation
The chemical equation for photosynthesis is:
6CO2 + 6H2O + Light Energy → C6H12O6 + 6O2

## Importance
Photosynthesis is essential for life on Earth as it produces the oxygen we breathe and forms the base of the food chain.`;
    
    const subject = document.getElementById('subjectSelect').value;
    const grade = document.getElementById('gradeSelect').value;
    
    document.getElementById('uploadSection').innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Processing sample content...</p>
            <p style="color: #aaa; font-size: 0.9rem;">This may take a few minutes</p>
        </div>
    `;
    
    fetch('/process_markdown', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            markdown: sampleMarkdown,
            subject: subject,
            grade: grade
        })
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'completed') {
            player.checkExistingPresentation();
        } else {
            alert('Processing failed: ' + (result.error || 'Unknown error'));
            location.reload();
        }
    })
    .catch(e => {
        alert('Processing failed: ' + e.message);
        location.reload();
    });
}

const player = new EducationPlayer();
