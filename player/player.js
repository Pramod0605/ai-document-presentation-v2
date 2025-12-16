let lessonData = null;

function getBasePath() {
  const path = window.location.pathname;
  const jobMatch = path.match(/\/player\/jobs\/([^\/]+)\//);
  if (jobMatch) {
    return `/player/jobs/${jobMatch[1]}/`;
  }
  return '/player/assets/';
}

const BASE_PATH = getBasePath();
const AVATAR_URL = "/player/assets/avatar_placeholder.mp4";

let currentSlideIndex = 0;
let isPlaying = false;
let currentBeatIndex = 0;
let beatVideoPaths = [];

async function detectBeatVideos(sectionId) {
  const beats = [];
  for (let i = 0; i < 20; i++) {
    const path = BASE_PATH + `videos/topic_${sectionId}_beat_${i}.mp4`;
    try {
      const resp = await fetch(path, { method: 'HEAD' });
      if (resp.ok) {
        beats.push(path);
      } else {
        break;
      }
    } catch (e) {
      break;
    }
  }
  return beats;
}

const stage = document.getElementById('stage');
const contentBox = document.getElementById('content-box');
const avatarCanvas = document.getElementById('avatar-canvas');
const video = document.getElementById('raw-avatar-video');
const audio = document.getElementById('main-audio');
const ctx = avatarCanvas.getContext('2d', { willReadFrequently: true });

let currentMedia = audio;

if (AVATAR_URL) {
  video.src = AVATAR_URL;
  video.load();
}

function updateVisuals() {
  const aScale = document.getElementById('av-scale').value;
  const aX = document.getElementById('av-x').value;
  const cScale = document.getElementById('con-scale').value;

  avatarCanvas.style.transform = `translateX(${aX}px) scale(${aScale})`;
  contentBox.style.transform = `scale(${cScale})`;
}

function renderAvatar() {
  if ((!video.paused && !video.ended) || video.readyState >= 2) {
    if (canvasSizeMismatch()) syncCanvasSize();
    if (avatarCanvas.width === 0 || avatarCanvas.height === 0) {
      requestAnimationFrame(renderAvatar);
      return;
    }

    ctx.drawImage(video, 0, 0, avatarCanvas.width, avatarCanvas.height);
    const frame = ctx.getImageData(0, 0, avatarCanvas.width, avatarCanvas.height);
    const data = frame.data;
    const thresh = parseInt(document.getElementById('av-green').value);

    for (let i = 0; i < data.length; i += 4) {
      const r = data[i], g = data[i + 1], b = data[i + 2];
      if (g > thresh && g > r * 1.3 && g > b * 1.3) data[i + 3] = 0;
    }
    ctx.putImageData(frame, 0, 0);
  }
  requestAnimationFrame(renderAvatar);
}

function canvasSizeMismatch() { return avatarCanvas.width !== video.videoWidth; }
function syncCanvasSize() { avatarCanvas.width = video.videoWidth; avatarCanvas.height = video.videoHeight; }

video.addEventListener('play', renderAvatar);
video.addEventListener('loadeddata', renderAvatar);

function loadSlide(index) {
  if (!lessonData || index >= lessonData.slides.length || index < 0) return;

  video.pause();
  audio.pause();

  currentSlideIndex = index;
  currentBeatIndex = 0;
  const slide = lessonData.slides[index];

  document.querySelectorAll('.slide-thumb').forEach((el, i) => {
    el.classList.toggle('active', i === index);
  });

  const slideTitle = slide.title || 'Untitled';
  if (document.getElementById('slide-title')) document.getElementById('slide-title').innerText = slideTitle;

  const list = document.getElementById('segments-list');
  list.innerHTML = '';

  const imgContainer = document.getElementById('slide-image-container');
  const bgImg = document.getElementById('bg-image-layer');
  const sceneLabel = document.getElementById('scene-label');

  const sectionType = slide.section_type || slide.slide_type || 'content';

  if (sectionType === 'example') {
    document.getElementById('content-box').classList.add('example-section');
  } else {
    document.getElementById('content-box').classList.remove('example-section');
  }

  if (sectionType === 'memory' && slide.flashcards) {
    const container = document.createElement('div');
    container.className = 'flashcard-container';
    slide.flashcards.forEach((fc, i) => {
      const card = document.createElement('div');
      card.className = 'flashcard';
      card.id = `seg-${i}`;
      card.innerHTML = `
        <div class="fc-question">${fc.question}</div>
        <div class="fc-answer">${fc.answer}</div>
      `;
      container.appendChild(card);
    });
    list.appendChild(container);
    document.getElementById('content-box').style.width = '70%';

    if (slide.audio_duration && !slide.timed_segments) {
      const durationPerItem = slide.audio_duration / slide.flashcards.length;
      slide.timed_segments = slide.flashcards.map((_, i) => ({
        start_time: i * durationPerItem,
        end_time: (i + 1) * durationPerItem
      }));
    }
  } else if (slide.visual_content && slide.visual_content.flashcards) {
    const container = document.createElement('div');
    container.className = 'flashcard-container';
    slide.visual_content.flashcards.forEach((fc, i) => {
      const card = document.createElement('div');
      card.className = 'flashcard';
      card.id = `seg-${i}`;
      card.innerHTML = `<div class="fc-letter">${fc.letter}</div><div class="fc-title">${fc.title}</div><div class="fc-desc">${fc.description}</div>`;
      container.appendChild(card);
    });
    list.appendChild(container);
    document.getElementById('content-box').style.width = '70%';

    if (slide.audio_duration && !slide.timed_segments) {
      const durationPerItem = slide.audio_duration / slide.visual_content.flashcards.length;
      slide.timed_segments = slide.visual_content.flashcards.map((_, i) => ({
        start_time: i * durationPerItem,
        end_time: (i + 1) * durationPerItem
      }));
    }
  } else {
    document.getElementById('content-box').style.width = '55%';

    let items = slide.timed_segments ||
      (slide.visual_content ? slide.visual_content.bullet_points : null) ||
      (slide.segments ? slide.segments.map(s => ({ visual: s.visual || s.text, start_time: s.start || 0, end_time: (s.start || 0) + (s.duration || 5) })) : []);

    if (Array.isArray(items)) {
      items.forEach((item, i) => {
        const div = document.createElement('div');
        div.className = 'segment-item';
        div.id = `seg-${i}`;
        div.innerHTML = typeof item === 'string' ? item : (item.visual || item.text || '');
        list.appendChild(div);
      });

      if (!slide.timed_segments && items.length > 0 && slide.audio_duration) {
        const durationPerItem = slide.audio_duration / items.length;
        slide.timed_segments = items.map((item, i) => ({
          visual: typeof item === 'string' ? item : (item.visual || item.text || ''),
          start_time: i * durationPerItem,
          end_time: (i + 1) * durationPerItem
        }));
      }
    }
  }

  if (window.MathJax) MathJax.typesetPromise();

  let isHeyGen = slide.use_heygen_audio || slide.video_path;

  if (isHeyGen) {
    currentMedia = video;
    let vidSrc = slide.avatar_video_url || slide.video_path;

    if (video.src.indexOf(vidSrc) === -1) {
      video.src = vidSrc;
    }
    video.muted = false;
    video.loop = false;
    audio.src = '';
  } else {
    let audSrc = slide.audio_path || '';
    if (audSrc && !audSrc.startsWith('http') && !audSrc.startsWith('/')) {
      audSrc = audSrc.replace(/^output\/v[34]-?[^/]*\//, '');
    }

    currentMedia = audio;

    if (video.src.indexOf(AVATAR_URL) === -1) {
      video.src = AVATAR_URL;
    }
    video.muted = true;
    video.loop = true;

    audio.src = audSrc;
  }

  if (currentMedia.readyState === 0) currentMedia.load();

  if (currentMedia !== video) {
    if (video.paused) video.play().catch(e => console.log("Auto-play loop failed", e));
  }

  if (isPlaying) {
    currentMedia.play();
    if (currentMedia === audio && video.paused) video.play();
  }

  bgImg.src = '';
  bgImg.style.opacity = 0;
  if (sceneLabel) {
    sceneLabel.innerText = '';
    sceneLabel.style.opacity = 0;
  }

  if (sectionType === 'intro') {
    stage.className = 'mode-center';
    document.getElementById('content-box').style.width = '80%';
  } else if (sectionType === 'recap') {
    stage.className = 'mode-image';
    const scenes = slide.recap_scenes || slide.storyboard_scenes;
    if (scenes && scenes.length > 0) {
      if (scenes[0].image_url) {
        bgImg.src = scenes[0].image_url;
        bgImg.style.opacity = 1;
      }
      if (sceneLabel) {
        sceneLabel.innerText = scenes[0].concept_title || scenes[0].description || 'Scene 1';
        sceneLabel.style.opacity = 1;
      }
    }
  } else if (sectionType === 'summary') {
    stage.className = 'mode-side';
    document.getElementById('content-box').style.width = '60%';
  } else if (sectionType === 'memory') {
    stage.className = 'mode-center';
    document.getElementById('content-box').style.width = '80%';
  } else {
    stage.className = 'mode-side';
    if (slide.image_id) {
      if (imgContainer) {
        imgContainer.style.display = 'block';
        imgContainer.innerHTML = `<img src="images/${slide.image_id}">`;
      }
      bgImg.src = "images/" + slide.image_id;
      bgImg.style.opacity = 0.2;
    } else {
      if (imgContainer) imgContainer.style.display = 'none';
      bgImg.src = '';
      bgImg.style.opacity = 0;
    }
  }

  updateVisuals();

  const bgVideo = document.getElementById('scene-video');
  const bgVidPath = slide.background_video;
  const contentVidPath = slide.content_video_path;

  if (contentVidPath && slide.has_content_video) {
    stage.classList.remove('mode-khan');
    stage.classList.add('mode-content-video');
    bgVideo.muted = true;
    bgVideo.loop = false;

    if (!bgVideo.src.includes(contentVidPath)) {
      bgVideo.src = contentVidPath;
      bgVideo.load();
    }
    bgVideo.style.opacity = 1;
    bgVideo.play().catch(e => console.log("Content Video Play Fail", e));
  } else if (bgVidPath) {
    stage.classList.remove('mode-content-video');
    stage.classList.add('mode-khan');

    if (bgVideo.src.indexOf(bgVidPath) === -1) {
      bgVideo.src = bgVidPath;
      bgVideo.load();
    }
    bgVideo.play().catch(e => console.log("BG Video Play Fail", e));
  } else {
    stage.classList.remove('mode-khan');
    stage.classList.remove('mode-content-video');
    bgVideo.pause();
    bgVideo.style.opacity = 0;
  }

  renderAvatar();
}

function handleTimeUpdate(e) {
  if (e.target !== currentMedia) return;

  const t = currentMedia.currentTime;
  const duration = currentMedia.duration;
  const slide = lessonData.slides[currentSlideIndex];

  if (duration && !isNaN(duration)) {
    document.getElementById('timeline-fill').style.width = (t / duration * 100) + '%';
  }
  document.getElementById('time-display').innerText = formatTime(t);

  const bgVideo = document.getElementById('scene-video');
  if (stage.classList.contains('mode-khan') && bgVideo) {
    if (isPlaying && bgVideo.paused) bgVideo.play();
    if (!isPlaying && !bgVideo.paused) bgVideo.pause();

    if (Math.abs(bgVideo.currentTime - t) > 0.5) {
      bgVideo.currentTime = t;
    }
  }

  if (stage.classList.contains('mode-content-video') && bgVideo) {
    if (isPlaying && bgVideo.paused) bgVideo.play();
    if (!isPlaying && !bgVideo.paused) bgVideo.pause();
    
    if (slide.beat_videos && slide.beat_videos.length > 1) {
      let targetBeatIndex = 0;
      
      if (slide.timed_segments && slide.timed_segments.length === slide.beat_videos.length) {
        for (let i = 0; i < slide.timed_segments.length; i++) {
          const seg = slide.timed_segments[i];
          if (t >= seg.start_time && t < seg.end_time) {
            targetBeatIndex = i;
            break;
          } else if (t >= seg.end_time) {
            targetBeatIndex = Math.min(i + 1, slide.beat_videos.length - 1);
          }
        }
      } else if (duration && !isNaN(duration)) {
        const beatDuration = duration / slide.beat_videos.length;
        targetBeatIndex = Math.min(Math.floor(t / beatDuration), slide.beat_videos.length - 1);
      }
      
      if (targetBeatIndex !== currentBeatIndex) {
        currentBeatIndex = targetBeatIndex;
        const newBeatPath = slide.beat_videos[targetBeatIndex];
        console.log(`Switching to beat ${targetBeatIndex}: ${newBeatPath}`);
        bgVideo.src = newBeatPath;
        bgVideo.load();
        bgVideo.play().catch(e => console.log("Beat video play fail", e));
      }
    } else {
      if (Math.abs(bgVideo.currentTime - t) > 0.5) {
        bgVideo.currentTime = t;
      }
    }
  }

  if (slide.timed_segments) {
    slide.timed_segments.forEach((seg, i) => {
      const el = document.getElementById(`seg-${i}`);
      if (!el) return;

      if (t >= seg.start_time && t < seg.end_time) {
        el.classList.add('active');
        el.classList.remove('read');
      } else if (t >= seg.end_time) {
        el.classList.remove('active');
        el.classList.add('read');
      } else {
        el.classList.remove('active');
        el.classList.remove('read');
      }
    });
  }

  const scenes = slide.recap_scenes || slide.storyboard_scenes;
  if (scenes && slide.timed_segments) {
    const sectionType = slide.section_type || slide.slide_type;
    if (sectionType === 'recap') {
      const segmentDuration = duration / scenes.length;
      scenes.forEach((scene, i) => {
        const sceneStart = i * segmentDuration;
        const sceneEnd = (i + 1) * segmentDuration;
        if (t >= sceneStart && t < sceneEnd) {
          const bg = document.getElementById('bg-image-layer');
          const label = document.getElementById('scene-label');

          if (scene.image_url && !bg.src.includes(scene.image_url)) {
            bg.src = scene.image_url;
            bg.style.opacity = 1;
          }
          if (label) {
            label.innerText = scene.concept_title || scene.description || `Scene ${i + 1}`;
          }
        }
      });
    }
  }
}

audio.addEventListener('timeupdate', handleTimeUpdate);
video.addEventListener('timeupdate', handleTimeUpdate);

function handleEnded(e) {
  if (e.target !== currentMedia) return;
  if (lessonData && currentSlideIndex < lessonData.slides.length - 1) {
    setTimeout(() => loadSlide(currentSlideIndex + 1), 1000);
  }
}
audio.addEventListener('ended', handleEnded);
video.addEventListener('ended', handleEnded);

function formatTime(s) {
  return `${Math.floor(s / 60)}:${Math.floor(s % 60).toString().padStart(2, '0')}`;
}

function togglePlay() {
  const bgVideo = document.getElementById('scene-video');
  
  if (currentMedia.paused) {
    currentMedia.play();
    if (currentMedia === audio) video.play();
    if (bgVideo && bgVideo.src && (stage.classList.contains('mode-khan') || stage.classList.contains('mode-content-video'))) {
      bgVideo.play().catch(e => {});
    }

    isPlaying = true;
    document.getElementById('btn-play').innerText = "Pause";
  } else {
    currentMedia.pause();
    if (currentMedia === audio) video.pause();
    if (bgVideo && !bgVideo.paused) {
      bgVideo.pause();
    }

    isPlaying = false;
    document.getElementById('btn-play').innerText = "Play";
  }
}

function prevSlide() {
  if (currentSlideIndex > 0) loadSlide(currentSlideIndex - 1);
}

function nextSlide() {
  if (lessonData && currentSlideIndex < lessonData.slides.length - 1) loadSlide(currentSlideIndex + 1);
}

document.getElementById('btn-play').onclick = togglePlay;
document.getElementById('btn-prev').onclick = prevSlide;
document.getElementById('btn-next').onclick = nextSlide;
document.getElementById('btn-dev').onclick = () => {
  document.getElementById('dev-panel').classList.toggle('show');
};
document.getElementById('btn-fullscreen').onclick = toggleFullScreen;

function toggleFullScreen() {
  if (!document.fullscreenElement) {
    stage.requestFullscreen().catch(err => {
      alert(`Error attempting to enable full-screen mode: ${err.message} (${err.name})`);
    });
  } else {
    document.exitFullscreen();
  }
}

document.getElementById('progress-container').onclick = (e) => {
  const rect = e.target.getBoundingClientRect();
  const pct = (e.clientX - rect.left) / rect.width;
  if (currentMedia.duration && !isNaN(currentMedia.duration)) {
    currentMedia.currentTime = pct * currentMedia.duration;
    if (currentMedia === audio && video.duration) {
      video.currentTime = pct * video.duration;
    }
  }
};

document.addEventListener('keydown', (e) => {
  if (e.code === 'Space') { e.preventDefault(); togglePlay(); }
  if (e.code === 'ArrowLeft') prevSlide();
  if (e.code === 'ArrowRight') nextSlide();
  if (e.code === 'KeyD') document.getElementById('dev-panel').classList.toggle('show');
});

function buildSlideList() {
  const container = document.getElementById('slide-list');
  container.innerHTML = '';
  if (!lessonData || !lessonData.slides) return;
  
  lessonData.slides.forEach((slide, i) => {
    const div = document.createElement('div');
    const sectionType = slide.section_type || slide.slide_type || 'content';
    div.className = 'slide-thumb' + (i === 0 ? ' active' : '');
    div.innerHTML = `<div class="num">${i + 1}</div><div class="type">${sectionType}</div>`;
    div.onclick = () => loadSlide(i);
    container.appendChild(div);
  });
}

async function checkExistingPresentation() {
  try {
    const response = await fetch(BASE_PATH + 'presentation.json');
    if (response.ok) {
      lessonData = await response.json();
      
      if (!lessonData.slides) {
        if (lessonData.sections) {
          lessonData.slides = lessonData.sections.map(section => ({
            slide_number: section.id,
            section_type: section.section_type || 'content',
            slide_type: section.section_type || 'content',
            title: section.title,
            segments: section.segments,
            flashcards: section.flashcards,
            recap_scenes: section.recap_scenes,
            timed_segments: section.segments ? section.segments.map(s => ({
              visual: s.text,
              start_time: s.start,
              end_time: s.start + s.duration
            })) : [],
            audio_path: BASE_PATH + `audio/section_${section.id}.mp3`,
            content_video_path: section.renderer === 'wan_video' ? BASE_PATH + `videos/topic_${section.id}.mp4` : null,
            has_content_video: section.renderer === 'wan_video',
            section_id: section.id,
            beat_videos: [],
            audio_duration: section.duration,
            full_narration: section.narration,
            visual_content: { bullet_points: section.segments ? section.segments.map(s => s.text) : [] }
          }));
        } else if (lessonData.topics) {
          lessonData.slides = lessonData.topics.map(topic => ({
            slide_number: topic.id,
            slide_type: 'content',
            section_type: 'content',
            title: topic.title,
            segments: topic.segments,
            timed_segments: topic.segments ? topic.segments.map(s => ({
              visual: s.text,
              start_time: s.start,
              end_time: s.start + s.duration
            })) : [],
            audio_path: BASE_PATH + `audio/topic_${topic.id}.mp3`,
            audio_duration: topic.duration,
            full_narration: topic.narration,
            visual_content: { bullet_points: topic.segments ? topic.segments.map(s => s.text) : [] }
          }));
        }
      }
      
      if (lessonData.slides && lessonData.slides.length > 0) {
        await detectAllBeatVideos();
        document.getElementById('upload-overlay').classList.add('hidden');
        buildSlideList();
        loadSlide(0);
        updateVisuals();
      }
    }
  } catch (e) {
    console.log('No existing presentation found');
  }
}

async function detectAllBeatVideos() {
  for (const slide of lessonData.slides) {
    if (slide.has_content_video && slide.section_id) {
      const beats = await detectBeatVideos(slide.section_id);
      if (beats.length > 0) {
        slide.beat_videos = beats;
        slide.content_video_path = beats[0];
        console.log(`Section ${slide.section_id}: Found ${beats.length} beat videos`);
      }
    }
  }
}

let currentJobId = null;
let pollInterval = null;

async function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);
  formData.append('subject', document.getElementById('subjectSelect').value);
  formData.append('grade', document.getElementById('gradeSelect').value);

  showLoading();

  try {
    const response = await fetch('/submit_job', {
      method: 'POST',
      body: formData
    });

    const result = await response.json();

    if (result.status === 'accepted' && result.job_id) {
      currentJobId = result.job_id;
      startPolling(result.job_id);
    } else if (result.status === 'busy') {
      alert('Another job is already processing. Please wait and try again.');
      location.reload();
    } else {
      alert('Job submission failed: ' + (result.error || 'Unknown error'));
      location.reload();
    }
  } catch (e) {
    alert('Upload failed: ' + e.message);
    location.reload();
  }
}

function showLoading() {
  document.getElementById('upload-box').innerHTML = `
    <div class="spinner"></div>
    <p>Processing your content...</p>
    <div class="progress-container">
      <div class="progress-bar">
        <div class="progress-fill" id="job-progress" style="width: 0%"></div>
      </div>
      <div class="progress-text" id="progress-text">Initializing...</div>
      <div class="step-indicator" id="step-indicator"></div>
    </div>
  `;
}

function updateProgress(status) {
  const progressBar = document.getElementById('job-progress');
  const progressText = document.getElementById('progress-text');
  const stepIndicator = document.getElementById('step-indicator');
  
  if (progressBar) progressBar.style.width = status.progress + '%';
  if (progressText) progressText.textContent = status.current_step || 'Processing...';
  if (stepIndicator) stepIndicator.textContent = `Step ${status.steps_completed + 1} of ${status.total_steps}`;
}

function startPolling(jobId) {
  if (pollInterval) clearInterval(pollInterval);
  
  pollInterval = setInterval(async () => {
    try {
      const response = await fetch(`/job/${jobId}/status`);
      const status = await response.json();
      
      updateProgress(status);
      
      if (status.status === 'completed') {
        clearInterval(pollInterval);
        pollInterval = null;
        await checkExistingPresentation();
      } else if (status.status === 'failed') {
        clearInterval(pollInterval);
        pollInterval = null;
        alert('Processing failed: ' + (status.error || 'Unknown error'));
        location.reload();
      }
    } catch (e) {
      console.error('Polling error:', e);
    }
  }, 1500);
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

  showLoading();

  fetch('/submit_job', {
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
      if (result.status === 'accepted' && result.job_id) {
        currentJobId = result.job_id;
        startPolling(result.job_id);
      } else if (result.status === 'busy') {
        alert('Another job is already processing. Please wait and try again.');
        location.reload();
      } else {
        alert('Job submission failed: ' + (result.error || 'Unknown error'));
        location.reload();
      }
    })
    .catch(e => {
      alert('Processing failed: ' + e.message);
      location.reload();
    });
}

document.getElementById('fileInput').addEventListener('change', handleFileUpload);

function showNewContentOverlay() {
  lessonData = null;
  currentSlideIndex = 0;
  
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
  
  document.getElementById('upload-box').innerHTML = `
    <h2>AI Animated Education</h2>
    <p>Upload PDF or Markdown file to generate educational videos</p>
    <input type="file" id="fileInput" accept=".pdf,.md,.markdown,.txt" style="display:none">
    <div style="margin-bottom: 15px;">
      <button class="upload-btn" onclick="document.getElementById('fileInput').click()">Upload PDF or Markdown</button>
    </div>
    <button class="upload-btn" style="background:#333" onclick="useSampleContent()">Try Sample Content</button>
    <div class="upload-selects">
      <select id="subjectSelect">
        <option value="General Science">General Science</option>
        <option value="Mathematics">Mathematics</option>
        <option value="Physics">Physics</option>
        <option value="Chemistry">Chemistry</option>
        <option value="Biology">Biology</option>
      </select>
      <select id="gradeSelect">
        <option value="8">Grade 8</option>
        <option value="9" selected>Grade 9</option>
        <option value="10">Grade 10</option>
      </select>
    </div>
    <p style="color:#666; font-size:0.8rem; margin-top:15px;">Supports: .pdf, .md, .markdown, .txt files</p>
  `;
  
  document.getElementById('fileInput').addEventListener('change', handleFileUpload);
  
  document.getElementById('upload-overlay').classList.remove('hidden');
}

document.getElementById('btn-new').onclick = showNewContentOverlay;

document.addEventListener('DOMContentLoaded', () => {
  checkExistingPresentation();
  updateVisuals();
});
