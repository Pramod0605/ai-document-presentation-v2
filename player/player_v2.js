/**
 * PLAYER V2 - Clean Unified Renderer
 * No legacy code - fresh implementation
 */

// ============================================
// CONFIGURATION
// ============================================
const AVATAR_URL = "/player/assets/avatar_placeholder.mp4";

// Determine job ID from URL parameter or derive from current path
const urlParams = new URLSearchParams(window.location.search);
const JOB_ID = urlParams.get('job');

// Derive BASE_PATH from current URL location when accessed directly from job folder
// e.g., /player/jobs/222f7012/index.html -> /player/jobs/222f7012/
const CURRENT_PATH = new URL('.', window.location.href).pathname;
const IS_JOB_FOLDER = CURRENT_PATH.includes('/jobs/') || CURRENT_PATH.includes('/player/jobs/');

// Set paths based on whether we have a job ID or are in a job folder
let BASE_PATH, PRESENTATION_PATH;
if (JOB_ID) {
  // Query parameter takes precedence
  BASE_PATH = `/player/jobs/${JOB_ID}/`;
  PRESENTATION_PATH = `/player/jobs/${JOB_ID}/presentation.json`;
  SOURCE_MARKDOWN_PATH = `/player/jobs/${JOB_ID}/source_markdown.md`;
} else if (IS_JOB_FOLDER) {
  // Derive from current path (baked player accessed directly)
  BASE_PATH = CURRENT_PATH;
  PRESENTATION_PATH = CURRENT_PATH + 'presentation.json';
  SOURCE_MARKDOWN_PATH = CURRENT_PATH + 'source_markdown.md';
} else {
  // Fallback to player_v2 assets folder
  BASE_PATH = '/player_v2/';
  PRESENTATION_PATH = 'presentation.json';
  SOURCE_MARKDOWN_PATH = 'source_markdown.md';
}

// Media path resolver - handles audio, video, avatar, and image paths
// CRITICAL: Handles Windows absolute paths stored in presentation.json
function resolveMediaPath(path, type = 'audio') {
  if (!path) return '';

  // STEP 1: Handle Windows absolute paths (C:\...) - extract just filename
  if (path.includes(':\\') || path.includes('\\')) {
    // Extract filename from Windows path
    const parts = path.split(/[\\\/]/);
    path = parts[parts.length - 1]; // Get just the filename
    console.log(`[V2.5] Extracted filename from Windows path: ${path}`);
  }

  // STEP 2: If path starts with / and contains /jobs/, extract relative portion
  if (path.startsWith('/jobs/') || path.startsWith('/player/jobs/')) {
    // Already a server-relative path, return as-is
    return path;
  }

  // STEP 3: If path is already HTTP URL, return as-is
  if (path.startsWith('http')) {
    return path;
  }

  // STEP 4: If path contains subfolder structure (avatars/, videos/, audio/)
  // but not a Windows path, prepend BASE_PATH
  if (path.includes('avatars/') || path.includes('videos/') || path.includes('audio/') || path.includes('images/')) {
    return BASE_PATH + path;
  }

  // STEP 5: Simple filename - prepend BASE_PATH + appropriate folder
  if (type === 'avatar') {
    return BASE_PATH + 'avatars/' + path;
  }
  if (type === 'video') {
    return BASE_PATH + 'videos/' + path;
  }
  if (type === 'image') {
    return BASE_PATH + 'images/' + path;
  }
  if (type === 'audio') {
    return BASE_PATH + 'audio/' + path;
  }

  return BASE_PATH + path;
}

// ============================================
// STATE
// ============================================
let lessonData = null;
let sourceMarkdown = "";
let slides = [];
let currentSlideIndex = 0;
let isPlaying = false;
let currentSegmentIndex = 0;

// DOM Elements
let stage, contentLayer, contentBox, avatarLayer, avatarVideo, avatarCanvas, avatarCtx;
let sectionTitle, headerTitle;
let videoLayer, contentVideo, narrationAudio;
let btnPlay, btnPrev, btnNext, slidePicker;
let timelineFill, timelineHandle, timeDisplay;
let devPanel, btnDev;

// Reveal state
let revealItems = [];
let chromaThreshold = 100;
let devModeEnabled = false;

// Time Source State (Avatar Video or Narration Audio)
let activeTimeSource = null; // Will be set to narrationAudio or avatarVideo in loadSlide


// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', init);

async function init() {
  cacheDOMElements();
  setupEventListeners();
  await loadPresentation();

  // Check URL hash for starting slide (#slide=N)
  const hash = window.location.hash;
  const match = hash.match(/slide=(\d+)/);
  if (match) {
    const startSlide = parseInt(match[1]);
    if (startSlide > 0 && startSlide <= slides.length) {
      loadSlide(startSlide - 1);
    }
  }
}

function cacheDOMElements() {
  stage = document.getElementById('stage');
  contentLayer = document.getElementById('content-layer');
  contentBox = document.getElementById('content-box');
  sectionTitle = document.getElementById('section-title');
  headerTitle = document.getElementById('header-title');
  avatarLayer = document.getElementById('avatar-layer');
  avatarVideo = document.getElementById('avatar-video');
  avatarCanvas = document.getElementById('avatar-canvas');
  avatarCtx = avatarCanvas.getContext('2d', { willReadFrequently: true });
  videoLayer = document.getElementById('video-layer');
  contentVideo = document.getElementById('content-video');
  narrationAudio = document.getElementById('narration-audio');
  btnPlay = document.getElementById('btn-play');
  btnPrev = document.getElementById('btn-prev');
  btnNext = document.getElementById('btn-next');
  slidePicker = document.getElementById('slide-picker');
  timelineFill = document.getElementById('timeline-fill');
  timelineHandle = document.getElementById('timeline-handle');
  timeDisplay = document.getElementById('time-display');
  devPanel = document.getElementById('dev-panel');
  btnDev = document.getElementById('btn-dev');
}

function setupEventListeners() {
  btnPlay.addEventListener('click', togglePlay);
  btnPrev.addEventListener('click', prevSlide);
  btnNext.addEventListener('click', nextSlide);
  slidePicker.addEventListener('change', (e) => loadSlide(parseInt(e.target.value)));

  slidePicker.addEventListener('change', (e) => loadSlide(parseInt(e.target.value)));

  // Audio/Time event listeners are now managed dynamically in bindTimeEvents() 
  // called from loadSlide() based on the active source.

  narrationAudio.onerror = (e) => {
    console.error('[V2] Audio error:', narrationAudio.error);
  };

  // Ensure we catch slide end even if source is narrationAudio (default)
  // This listener is persistent as a fallback, but specific timeupdates are dynamic
  narrationAudio.addEventListener('ended', () => {
    if (activeTimeSource === narrationAudio) onSlideEnd();
  });


  narrationAudio.onerror = (e) => {
    console.error('[V2] Audio failed to load:', narrationAudio.src);
    // Fallback to timer if audio fails
    if (activeTimeSource === narrationAudio) {
      console.warn('[V2] Switching to Timer Fallback due to audio error');
      activeTimeSource = timerFallback;
      // Recalculate duration just in case
      const duration = getTotalDuration(slides[currentSlideIndex]);
      timerFallback.reset(duration);

      bindTimeEvents(timerFallback);

      showSilentModeIndicator(true);

      if (isPlaying) {
        timerFallback.play();
      }
    }
  };

  contentVideo.addEventListener('ended', onContentVideoEnd);
  contentVideo.onerror = (e) => {
    // Only log if src was actually set (some sections like Intro/Summary have no content video)
    if (contentVideo.src && !contentVideo.src.includes('player_v2')) {
      console.error('[V2] Content video error:', contentVideo.error);
    }
  };

  document.getElementById('timeline-track').addEventListener('click', seekTimeline);
  document.getElementById('btn-fullscreen').addEventListener('click', toggleFullscreen);

  // Dev panel controls
  if (btnDev) btnDev.addEventListener('click', toggleDevPanel);
  setupDevControls();

  document.addEventListener('keydown', handleKeyboard);

  // Avatar video setup with chroma keying
  avatarVideo.onerror = (e) => {
    console.error('[V2] Avatar video error:', avatarVideo.error);
    showAvatarPlaceholder();
  };

  avatarVideo.onloadeddata = () => {
    console.log('[V2] Avatar video loaded, starting chroma key');
    syncCanvasSize();
    // Try autoplay - if blocked, user will need to click play button
    // DO NOT show placeholder - avatar will play when user clicks play
    avatarVideo.play().catch(e => {
      console.log('[V2] Avatar autoplay blocked (normal) - will play on user click:', e.name);
      // Keep canvas visible, don't show placeholder
    });
  };

  avatarVideo.addEventListener('play', startChromaKeyLoop);

  // Avatar will be loaded per-slide in setupMediaSource
  // Don't load placeholder here - it causes the issue
}

function showAvatarPlaceholder() {
  // Show a placeholder when avatar video fails
  avatarCanvas.style.display = 'none';
  const existing = document.getElementById('avatar-placeholder');
  if (existing) return;

  const placeholder = document.createElement('div');
  placeholder.id = 'avatar-placeholder';
  placeholder.innerHTML = `
    <div style="width: 200px; height: 200px; background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 40px rgba(99, 102, 241, 0.5);">
      <svg width="100" height="100" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5">
        <circle cx="12" cy="8" r="4"/>
        <path d="M4 20v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1"/>
      </svg>
    </div>
    <p style="color: #a5b4fc; margin-top: 16px; font-size: 14px;">AI Instructor</p>
  `;
  placeholder.style.cssText = 'display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%;';
  avatarLayer.appendChild(placeholder);
}

// ============================================
// TIME SOURCE MANAGEMENT
// ============================================

// Timer-based fallback for when no audio/video is available
// Allows playback using WPM-calculated durations from presentation.json
let timerFallback = {
  currentTime: 0,
  duration: 30,
  _interval: null,
  _eventListeners: { timeupdate: [], ended: [] },

  play: function () {
    if (this._interval) return Promise.resolve();
    this._interval = setInterval(() => {
      this.currentTime += 0.1;
      this._eventListeners.timeupdate.forEach(fn => fn());
      if (this.currentTime >= this.duration) {
        this.pause();
        this._eventListeners.ended.forEach(fn => fn());
      }
    }, 100);
    console.log('[V2] Timer fallback playing (no media)');
    return Promise.resolve();
  },

  pause: function () {
    if (this._interval) {
      clearInterval(this._interval);
      this._interval = null;
    }
  },

  addEventListener: function (event, fn) {
    if (this._eventListeners[event]) this._eventListeners[event].push(fn);
  },

  removeEventListener: function (event, fn) {
    if (this._eventListeners[event]) {
      this._eventListeners[event] = this._eventListeners[event].filter(f => f !== fn);
    }
  },

  reset: function (duration) {
    this.pause();
    this.currentTime = 0;
    this.duration = duration || 30;
  }
};

let useTimerFallback = false; // Flag to track if we're using timer

function getTime() {
  if (useTimerFallback) return timerFallback.currentTime;
  return activeTimeSource ? activeTimeSource.currentTime : 0;
}

function getDuration() {
  if (useTimerFallback) return timerFallback.duration;
  return activeTimeSource ? (activeTimeSource.duration || 1) : 1;
}

function bindTimeEvents(source) {
  if (!source) return;

  // Unbind from previous source if needed (though listeners are specific to element)
  // We just ensure we add to the new source

  source.addEventListener('timeupdate', handleTimeUpdateMain);
  source.addEventListener('ended', onSlideEnd);

  console.log('[V2] Bound time events to:', source.id);
}

function unbindTimeEvents(source) {
  if (!source) return;

  source.removeEventListener('timeupdate', handleTimeUpdateMain);
  source.removeEventListener('ended', onSlideEnd);

  console.log('[V2] Unbound time events from:', source.id);
}

function handleTimeUpdateMain() {
  // Central handler for all time-based updates
  updateTimeline();
  updateContentPages();
  // Sync beat video needs explicit time passing or refactoring
  syncBeatVideoToAudio(getTime());

  // V2.5: Update display state based on directives
  updateDisplayState();

  // V2.5: Progressive reveal for Summary bullets
  updateSummaryProgressiveReveal();
}

// V2.5: Progressive reveal for Summary section bullets
// Reveals bullets one-by-one based on current playback time
function updateSummaryProgressiveReveal() {
  const slide = slides[currentSlideIndex];
  if (!slide || slide.section_type !== 'summary') return;

  const bulletCount = window.summaryBulletCount || 0;
  if (bulletCount === 0) return;

  const currentTime = getTime();
  const totalDuration = getDuration() || 30;

  // Calculate which bullet should be visible based on time progress
  // Each bullet gets equal time: totalDuration / bulletCount
  const timePerBullet = totalDuration / bulletCount;
  const bulletsToShow = Math.floor(currentTime / timePerBullet) + 1;

  // Reveal bullets up to current time
  for (let i = 0; i < Math.min(bulletsToShow, bulletCount); i++) {
    const bullet = document.getElementById(`summary-bullet-${i}`);
    if (bullet && bullet.classList.contains('reveal-hidden')) {
      bullet.classList.remove('reveal-hidden');
      bullet.classList.add('reveal-visible');
      console.log(`[V2.5] Summary: Revealed bullet ${i + 1}/${bulletCount}`);
    }
  }
}

function updateDisplayState() {
  if (!slides[currentSlideIndex]) return;

  const currentTime = getTime();
  // We need to find the *latest* directive that has passed
  const directives = parseDisplayDirectives(slides[currentSlideIndex]);
  let activeDirective = null;

  for (const dir of directives) {
    if (currentTime >= dir.time) {
      activeDirective = dir;
    } else {
      break;
    }
  }

  if (activeDirective) {
    const action = activeDirective.action;
    const data = activeDirective.data;

    if (action === 'show_video') {
      videoLayer.classList.add('fullscreen');
      videoLayer.classList.remove('hidden');
      contentLayer.style.opacity = '0';
      // Ensure avatar is visible (overlay)
      if (avatarLayer) avatarLayer.style.opacity = '1';
    } else if (action === 'show_text') {
      videoLayer.classList.remove('fullscreen');
      videoLayer.classList.add('hidden');
      contentLayer.style.opacity = '1';
    } else if (action === 'flip_card') {
      const cardIndex = data.card_index || 0;
      const card = document.getElementById(`flashcard-${cardIndex}`);
      if (card && card.dataset.flipped !== 'true') {
        card.classList.add('flipped');
        card.dataset.flipped = 'true';
      }
    } else if (action === 'reveal_answer') {
      const qIndex = data.question_index || 0;
      const quiz = document.getElementById(`quiz-${qIndex}`);
      if (quiz && !quiz.classList.contains('revealed')) {
        quiz.classList.add('revealed');
        const slide = slides[currentSlideIndex];
        if (slide.quiz_questions && slide.quiz_questions[qIndex]) {
          const correctIndex = slide.quiz_questions[qIndex].correct_option;
          const choices = quiz.querySelectorAll('.quiz-choice');
          if (choices[correctIndex]) {
            choices[correctIndex].classList.add('correct-revealed');
            const letter = choices[correctIndex].querySelector('.choice-letter');
            if (letter) letter.classList.add('correct');
          }
        }
      }
    } else if (action === 'pause') {
      // Handled by pause logic, mostly UI indication could be added here
    }
  } else {
    // Default state: Content visible, Video hidden (unless it's recap/intro logic handled elsewhere)
    // Only verify if we are in a content slide and NO directive has triggered yet
    // This prevents flickering if we are just starting
    if (slides[currentSlideIndex].section_type === 'content' && !videoLayer.classList.contains('fullscreen')) {
      // contentLayer.style.opacity = '1'; 
      // We leave it as set by renderContent defaults
    }
  }
}

// ============================================
// CHROMA KEYING (Green Screen Removal)
// ============================================
function syncCanvasSize() {
  if (avatarVideo.videoWidth > 0 && avatarVideo.videoHeight > 0) {
    avatarCanvas.width = avatarVideo.videoWidth;
    avatarCanvas.height = avatarVideo.videoHeight;
  }
}

function startChromaKeyLoop() {
  requestAnimationFrame(renderChromaFrame);
}

function renderChromaFrame() {
  // Continue rendering regardless of video state to keep canvas updated
  if (avatarVideo.readyState < 2) {
    // Video not ready yet, retry next frame
    requestAnimationFrame(renderChromaFrame);
    return;
  }

  // Sync canvas size if video size changed
  if (avatarCanvas.width !== avatarVideo.videoWidth && avatarVideo.videoWidth > 0) {
    syncCanvasSize();
  }

  // Skip if canvas not ready
  if (avatarCanvas.width === 0 || avatarCanvas.height === 0) {
    requestAnimationFrame(renderChromaFrame);
    return;
  }

  try {
    // Draw current video frame
    avatarCtx.drawImage(avatarVideo, 0, 0, avatarCanvas.width, avatarCanvas.height);

    // Get pixel data
    const frame = avatarCtx.getImageData(0, 0, avatarCanvas.width, avatarCanvas.height);
    const data = frame.data;

    // Chroma key: Make green pixels transparent
    for (let i = 0; i < data.length; i += 4) {
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];

      // Green screen detection: green > threshold AND green > red*1.3 AND green > blue*1.3
      if (g > chromaThreshold && g > r * 1.3 && g > b * 1.3) {
        data[i + 3] = 0; // Set alpha to 0 (transparent)
      }
    }

    avatarCtx.putImageData(frame, 0, 0);
  } catch (e) {
    // Security error or other issue - show placeholder
    console.error('[V2] Chroma key error:', e);
  }

  requestAnimationFrame(renderChromaFrame);
}

// ... existing imports ...

// --- Markdown Parsing Utilities ---
function parseSourceMarkdown(markdown) {
  if (!markdown) return [];

  const lines = markdown.split('\n');
  const sections = [];
  let currentSection = { title: '', content: [] };

  lines.forEach(line => {
    // Check for headers (mapped to sections)
    if (line.match(/^#{1,3}\s/)) {
      if (currentSection.title || currentSection.content.length > 0) {
        sections.push(currentSection);
      }
      currentSection = {
        title: line.replace(/^#{1,3}\s/, '').trim(),
        content: []
      };
    } else {
      currentSection.content.push(line);
    }
  });

  if (currentSection.title || currentSection.content.length > 0) {
    sections.push(currentSection); // Push last section
  }

  return sections;
}

async function loadPresentation() {
  try {
    const response = await fetch(PRESENTATION_PATH);
    lessonData = await response.json();
    slides = lessonData.sections || [];

    // V2.5 Director Mode: Fetch source markdown and map to sections
    try {
      const mdResponse = await fetch(SOURCE_MARKDOWN_PATH);
      if (mdResponse.ok) {
        sourceMarkdown = await mdResponse.text();
        console.log(`[V2.5] Source Markdown loaded: ${sourceMarkdown.length} chars`);

        const parsedSections = parseSourceMarkdown(sourceMarkdown);
        console.log(`[V2.5] Parsed ${parsedSections.length} markdown sections`);

        // Map parsed markdown to slides
        slides.forEach((slide, index) => {
          // 1. Try exact Title match
          let match = parsedSections.find(p => p.title.toLowerCase().trim() === slide.title?.toLowerCase().trim());

          // 2. Try Partial Title match
          if (!match) {
            match = parsedSections.find(p => p.title.toLowerCase().includes(slide.title?.toLowerCase() || 'xxx'));
          }

          // 3. Try Section Type Mapping (Robust Fallback)
          if (!match && slide.section_type) {
            const type = slide.section_type.toLowerCase();
            // Map 'summary' -> 'Summary' or 'Learning Objectives'
            if (type === 'summary') {
              match = parsedSections.find(p => p.title.toLowerCase().includes('summary') || p.title.toLowerCase().includes('learning objectives'));
            } else if (type === 'intro') {
              match = parsedSections.find(p => p.title.toLowerCase().includes('introduction'));
            } else if (type === 'quiz') {
              match = parsedSections.find(p => p.title.toLowerCase().includes('exercise') || p.title.toLowerCase().includes('quiz'));
            }
          }

          // 4. Fallback index
          const fallback = parsedSections[index];

          if (match) {
            console.log(`[V2.5] Mapped Slide '${slide.title}' to MD Section '${match.title}'`);
            slide.markdown_content = match.content.filter(l => l.trim() !== '');
          } else if (fallback) {
            // Weak index matching fallback
            slide.markdown_content = fallback.content.filter(l => l.trim() !== '');
          }
        });

      } else {
        console.warn("[V2.5] source_markdown.md not found.");
      }
    } catch (e) {
      console.warn("[V2.5] Failed to load source_markdown.md", e);
    }


    // Set header title from presentation
    if (headerTitle && lessonData.title) {
      headerTitle.textContent = lessonData.title;
    }

    populateSlidePicker();

    if (slides.length > 0) {
      loadSlide(0);
    }
  } catch (error) {
    console.error('Failed to load presentation:', error);
    contentBox.innerHTML = '<p style="color: #f87171;">Failed to load presentation. Check console for details.</p>';
  }
}

function populateSlidePicker() {
  slidePicker.innerHTML = '';
  slides.forEach((slide, i) => {
    const option = document.createElement('option');
    option.value = i;
    option.textContent = `${i + 1}. ${slide.section_type}: ${slide.title || 'Untitled'}`.substring(0, 40);
    slidePicker.appendChild(option);
  });
}

// ============================================
// SLIDE RENDERER (Main Entry Point)
// ============================================
function loadSlide(index) {
  if (index < 0 || index >= slides.length) return;

  currentSlideIndex = index;
  currentSegmentIndex = 0;
  slidePicker.value = index;
  revealItems = []; // Reset reveal state
  displayDirectivesApplied = false; // Reset for new slide

  // CRITICAL: Reset beat playlist to prevent Section N inheriting Section N-1's beats
  beatVideoPlaylist = [];
  currentBeatIndex = -1;

  const slide = slides[index];
  const sectionType = slide.section_type || 'content';

  console.log(`[V2] Loading slide ${index + 1}: ${sectionType} - ${slide.title || 'Untitled'}`);

  // Stop any playing media first
  if (activeTimeSource) {
    activeTimeSource.pause();
    activeTimeSource.currentTime = 0;
    unbindTimeEvents(activeTimeSource);
  }

  contentVideo.pause();
  contentVideo.src = '';

  // Reset all layer states for new slide
  contentBox.innerHTML = '';
  videoLayer.classList.add('hidden');
  contentLayer.classList.remove('video-mode');

  // Set section title
  if (sectionType !== 'intro' && slide.title) {
    sectionTitle.textContent = slide.title;
    sectionTitle.style.display = 'flex';
  } else {
    sectionTitle.textContent = '';
    sectionTitle.style.display = 'none';
  }

  setStageMode(sectionType);

  switch (sectionType) {
    case 'intro':
      renderIntro(slide);
      break;
    case 'summary':
      renderSummary(slide);
      break;
    case 'quiz':
      renderQuiz(slide);
      break;
    case 'memory':
      renderMemory(slide);
      break;
    case 'recap':
      // Recap uses renderContent which has special isRecap handling for video-only mode
      renderContent(slide);
      break;
    case 'content':
    case 'example':
    default:
      renderContent(slide);
      break;
  }

  setupMediaSource(slide);

  // Update header title to show current section title
  if (headerTitle) {
    if (sectionType === 'intro') {
      headerTitle.textContent = lessonData?.lesson_title || 'Lesson';
    } else {
      headerTitle.textContent = slide.title || lessonData?.lesson_title || 'Lesson';
    }
  }

  requestAnimationFrame(async () => {
    fitContentToContainer(contentBox);
    // Setup content splitting after layout is calculated
    setupContentSplitting(slide);
    // Setup progressive reveal for rendered items
    setupProgressiveReveal(slide);
    // Update dev panel info
    updateDevInfo();

    // Typeset LaTeX after content is rendered
    await typesetMath(contentBox);

    // V2.5: Preload next section media
    if (typeof preloadNextSection === 'function') {
      preloadNextSection(index + 1);
    }
  });
}

// ============================================
// MEDIA SOURCE SETUP (Avatar, Audio, Video)
// ============================================
function setupMediaSource(slide) {
  const sectionType = slide.section_type || 'content';

  // CRITICAL: Stop and unbind any existing time source before setting up a new one
  if (activeTimeSource) {
    activeTimeSource.pause();
    unbindTimeEvents(activeTimeSource);
    activeTimeSource = null;
  }

  // 1. Setup AVATAR (job-specific path per slide)
  let avatarPath = slide.avatar_video_path || slide.avatar_video;

  // FALLBACK: If no avatar path for this slide (e.g., Summary), try using the Intro avatar
  // This is a temporary hotfix to ensure timing works even if generation skipped a section
  if (!avatarPath && slides[0] && (slides[0].avatar_video || slides[0].avatar_video_path)) {
    console.warn('[V2] No avatar for this slide - falling back to INTRO avatar for timing');
    avatarPath = slides[0].avatar_video || slides[0].avatar_video_path;
  }

  // Always reset avatar state first
  avatarVideo.pause();
  avatarVideo.removeAttribute('src'); // Clear previous source

  if (avatarPath) {
    const fullAvatarPath = resolveMediaPath(avatarPath, 'avatar');
    console.log(`[V2] Setting Avatar URL: ${fullAvatarPath}`); // User requested explicit log

    // Hide placeholder if it exists
    const placeholder = document.getElementById('avatar-placeholder');
    if (placeholder) placeholder.remove();
    avatarCanvas.style.display = 'block';

    avatarVideo.src = fullAvatarPath;
    avatarVideo.muted = true; // CRITICAL for autoplay
    avatarVideo.loop = false; // V2.5: Should not loop narration
    avatarVideo.playsInline = true;
    avatarVideo.load();

    avatarVideo.onloadeddata = () => {
      console.log('[V2] Avatar loaded successfully');
      syncCanvasSize();
      // Auto-play avatar (muted, so should work)
      avatarVideo.play().catch(e => {
        console.warn('[V2] Avatar autoplay failed (rare):', e);
        // Don't show placeholder - video is loaded, user just needs to click play
      });
    };

    avatarVideo.onplay = () => console.log('[V2] Avatar STARTED playing');
    avatarVideo.onpause = () => console.log('[V2] Avatar PAUSED');

    avatarVideo.onerror = (e) => {
      console.error('[V2] Avatar failed to load:', e);
      // If avatar fails, we might need to fallback to timer logic dynamically
      // But for now, let's just log it.
    };

  } else {
    console.warn('[V2] No avatar path found for this slide');
    showAvatarPlaceholder();
  }

  // 2. V2.5 TIME SOURCE SETUP
  // V2.5 Architecture: NO separate MP3 audio files
  // Time source priority: Avatar Video (MP4) → Timer Fallback
  if (avatarPath) {
    // PRIMARY: Use avatar video as time source (has embedded audio)
    activeTimeSource = avatarVideo;
    useTimerFallback = false;
    bindTimeEvents(avatarVideo);
    console.log('[V2.5] Using Avatar Video as Time Source');
  } else {
    // FALLBACK: Use timer when no avatar available
    const duration = getTotalDuration(slide);
    timerFallback.reset(duration);
    activeTimeSource = timerFallback;
    useTimerFallback = true;
    bindTimeEvents(timerFallback);
    showSilentModeIndicator(true);
    console.log(`[V2.5] No avatar - using timer fallback (${duration.toFixed(1)}s)`);
  }

  // 3. Setup CONTENT VIDEO (if applicable - handled by renderContent)
  // Beat videos are loaded separately in loadBeatVideo()
}

function getTotalDuration(slide) {
  const segments = slide.narration?.segments || [];
  return segments.reduce((sum, seg) => sum + (seg.duration_seconds || 5), 0) || 30;
}

function showSilentModeIndicator(show) {
  console.log('[V2] 🔇 Silent Mode: No audio available, using timer');
}

function renderIntro(slide) {
  console.log('[V2] IntroRenderer: Clean avatar-only start');
  // Intro handles its own clean layout via setStageMode('intro')
  contentBox.innerHTML = '';
  // Optionally add a welcome message or title if desired, but Bible says "Clean Start"
}

function setStageMode(sectionType) {
  stage.className = '';

  if (sectionType === 'intro') {
    stage.classList.add('mode-intro');
    contentLayer.classList.add('hidden');
  } else {
    contentLayer.classList.remove('hidden');
  }
}

function renderSummary(slide) {
  console.log('[V2] SummaryRenderer: Level-1 bullets with checkmarks');

  const contentBox = document.getElementById('content-box');
  contentBox.innerHTML = '';

  // Title if needed (usually handled by slide title element, but we can add header)
  const header = document.createElement('h2');
  header.className = 'summary-header';
  header.textContent = slide.title || 'Summary';
  contentBox.appendChild(header);

  // V2.5 Summary Mode Priority:
  // 1. Visual Beats (Director Standard)
  // 2. Slide Visual Content (Global Fallback)
  // 3. Narration Segments (Legacy/Aligned)

  const collectedBullets = new Set();

  // Strategy 1: Visual Beats (Primary for V2.5)
  if (slide.visual_beats && slide.visual_beats.length > 0) {
    console.log(`[V2] SummaryRenderer: Found ${slide.visual_beats.length} visual beats`);
    slide.visual_beats.forEach(beat => {
      if (beat.visual_type === 'bullet_list' && beat.display_text) {
        // display_text can be a string OR an array
        if (Array.isArray(beat.display_text)) {
          beat.display_text.forEach(item => {
            const text = (typeof item === 'string' ? item : (item.text || '')).trim();
            if (text) collectedBullets.add(sanitizeMarkdown(text));
          });
        } else if (typeof beat.display_text === 'string') {
          const text = beat.display_text.trim();
          if (text) collectedBullets.add(sanitizeMarkdown(text));
        }
      }
    });
  }

  // Strategy 2: Slide-Level Visual Content
  if (collectedBullets.size === 0 && slide.visual_content?.bullet_points) {
    console.log('[V2] SummaryRenderer: Found slide-level bullets');
    slide.visual_content.bullet_points.forEach(bp => {
      const text = (typeof bp === 'string' ? bp : (bp.text || '')).trim();
      if (!bp.level || bp.level === 1) {
        collectedBullets.add(sanitizeMarkdown(text));
      }
    });
  }

  // Strategy 3: Narration Segments (Fallback)
  if (collectedBullets.size === 0) {
    const segments = slide.narration?.segments || [];
    segments.forEach(seg => {
      const vc = seg.visual_content;
      const bulletData = vc?.bullet_points || vc?.items || [];
      if (bulletData.length > 0) {
        bulletData.forEach(bp => {
          const text = (typeof bp === 'string' ? bp : (bp.text || '')).trim();
          if (text.toLowerCase().includes('thinking')) return;
          if (!bp.level || bp.level === 1) {
            collectedBullets.add(sanitizeMarkdown(text));
          }
        });
      }
    });
  }

  // Final Rendering
  const allBulletsArray = Array.from(collectedBullets);

  if (allBulletsArray.length === 0) {
    // Last ditch: check markdown content if allowed
    if (slide.markdown_content && slide.markdown_content.length > 0) {
      console.log('[V2] SummaryRenderer: Fallback to markdown source');
      const contentDiv = document.createElement('div');
      contentDiv.className = 'summary-markdown-wrapper';
      contentDiv.innerHTML = sanitizeMarkdown(slide.markdown_content.join('\n'));
      contentBox.appendChild(contentDiv);
      return;
    }

    const p = document.createElement('p');
    p.className = 'paragraph-block';
    p.textContent = 'Summary content';
    contentBox.appendChild(p);
    return;
  }

  const list = document.createElement('ul');
  list.className = 'summary-list';

  // V2.5: Add bullets with reveal-hidden class for progressive reveal
  allBulletsArray.forEach((text, i) => {
    const item = document.createElement('li');
    item.className = 'summary-item reveal-hidden'; // Hidden initially
    item.id = `summary-bullet-${i}`;
    item.dataset.index = i;
    item.innerHTML = `
      <span class="summary-marker">✓</span>
      <span class="summary-text">${text}</span>
    `;
    list.appendChild(item);
  });

  contentBox.appendChild(list);

  // Store bullet count for progressive reveal logic
  window.summaryBulletCount = allBulletsArray.length;
  window.summaryBulletsRevealed = 0;
  console.log(`[V2.5] Summary: ${allBulletsArray.length} bullets ready for progressive reveal`);
}

function renderContent(slide) {
  console.log('[V2] ContentRenderer: Paragraphs, bullets, formulas');

  // Check if this slide has a Manim/WAN video to display
  const videoPath = slide.video_path || slide.content_video_path;
  const renderer = slide.renderer || 'none';
  const beatVideoPaths = slide.beat_video_paths || [];
  const sectionType = slide.section_type || 'content';
  const hasVideo = videoPath && (renderer === 'manim' || renderer === 'wan_video' || renderer === 'wan' || renderer === 'video');
  const hasMultiBeat = beatVideoPaths.length > 1 && hasVideo;

  // TEACH → SHOW Pattern: Always render text content first (except for recap which is video-only)
  const segments = slide.narration?.segments || [];
  const isRecap = sectionType === 'recap';

  // Render text content FIRST (unless this is a recap section which is video-only)
  if (!isRecap) {
    // [V2.5] MARKDOWN SOURCE TRUTH
    // If we have parsed markdown content, use THAT for the visual text.
    // Narration segments are still valid for timing, but we decouple text display.
    if (slide.markdown_content && slide.markdown_content.length > 0) {
      console.log(`[V2.5] Rendering from Markdown Source(${slide.markdown_content.length} lines)`);

      slide.markdown_content.forEach((line, i) => {
        const para = document.createElement('div');
        para.className = 'paragraph-block';
        para.id = `md - block - ${i} `; // Use md- prefix to avoid sync issues with segments for now
        // Basic markdown sanitization/conversion could happen here
        para.innerHTML = sanitizeMarkdown(line);
        contentBox.appendChild(para);
      });

    } else if (segments.length > 0) {
      // Fallback to legacy segment-based rendering
      console.log(`[V2] ContentRenderer: Rendering ${segments.length} segments with visual_content`);

      segments.forEach((seg, i) => {
        if (isThinkingSegment(seg)) {
          const placeholder = document.createElement('div');
          placeholder.id = `seg - ${i} `;
          placeholder.style.display = 'none';
          contentBox.appendChild(placeholder);
          return;
        }

        const segDiv = document.createElement('div');
        segDiv.className = 'segment-block';
        segDiv.id = `seg - ${i} `;

        const vc = seg.visual_content;
        if (vc) {
          renderVisualContent(vc, segDiv);
        } else if (seg.text) {
          const para = document.createElement('div');
          para.className = 'paragraph-block';
          para.innerHTML = sanitizeMarkdown(seg.text);
          segDiv.appendChild(para);
        }

        if (segDiv.children.length > 0) {
          contentBox.appendChild(segDiv);
        }
      });

      const firstSeg = document.getElementById('seg-0');
      if (firstSeg) firstSeg.classList.add('segment-active');
    }
  }

  // Now handle video loading (for both content and recap sections)
  // For content sections: video will overlay based on flip_timing_sec
  // For recap sections: video-only mode

  // Multi-beat video mode
  if (hasMultiBeat) {
    console.log(`[V2] ContentRenderer: Multi - beat video mode - ${beatVideoPaths.length} videos`);

    beatVideoPlaylist = buildBeatPlaylistWithTiming(slide);
    currentBeatIndex = -1;

    if (beatVideoPlaylist.length > 0) {
      console.log(`[V2] Content beat playlist built with ${beatVideoPlaylist.length} videos`);
      beatVideoPlaylist.forEach((b, i) => {
        console.log(`  Beat ${i}: ${b.videoPath} (${b.startTime.toFixed(1)} s - ${b.endTime.toFixed(1)}s)`);
      });

      if (isRecap) {
        // Recap: show video immediately (video-only mode - hides content)
        videoLayer.classList.remove('hidden');
        contentLayer.classList.add('video-mode');
      } else {
        // Content: hide video initially, display_directives controls visibility during playback
        // DO NOT add video-mode - content (text/images) must remain visible
        videoLayer.classList.add('hidden');
      }
      loadBeatVideo(0);
    }
    return;
  }

  // Single video mode
  if (hasVideo) {
    console.log(`[V2] ContentRenderer: Single video mode - ${videoPath} `);
    const fullPath = resolveMediaPath(videoPath, 'video');
    console.log(`[V2] Loading content video: ${fullPath} `);

    if (isRecap) {
      // Recap: show video immediately (video-only mode - hides content)
      videoLayer.classList.remove('hidden');
      contentLayer.classList.add('video-mode');
    } else {
      // Content: hide video initially, display_directives controls visibility during playback
      // DO NOT add video-mode - content (text/images) must remain visible
      videoLayer.classList.add('hidden');
    }

    contentVideo.muted = true;
    contentVideo.loop = true;
    contentVideo.playsInline = true;
    contentVideo.src = fullPath;
    contentVideo.load();
    contentVideo.playbackRate = 1.0;
    contentVideo.onloadeddata = () => {
      console.log(`[V2] Content video loaded successfully: ${fullPath} `);
      if (isPlaying && isRecap) {
        contentVideo.play().catch(e => console.warn('[V2] Content video play failed:', e));
      }
    };
    return;
  }

  // No video - fallback for slide-level visual_content when no segments exist
  if (segments.length === 0) {
    const vc = slide.visual_content;
    if (vc) {
      renderVisualContent(vc, contentBox);
    }
  }
}

// ============================================
// V2.5 COMPLIANCE FUNCTIONS FOR PLAYER_V2.JS
// Insert after line 932 (after renderContent function)
// ============================================

// QUIZ RENDERER (V2.5 Compliance)
function renderQuiz(slide) {
  console.log('[V2.5] QuizRenderer: 3-step dance');

  const contentBox = document.getElementById('content-box');
  contentBox.innerHTML = '';

  const questions = slide.quiz_questions || [];

  questions.forEach((q, qIndex) => {
    const quizCard = document.createElement('div');
    quizCard.className = 'quiz-card quiz-hidden';
    quizCard.id = `quiz-${qIndex}`;

    const questionDiv = document.createElement('div');
    questionDiv.className = 'quiz-question';
    questionDiv.textContent = q.question;
    quizCard.appendChild(questionDiv);

    const choicesDiv = document.createElement('div');
    choicesDiv.className = 'quiz-choices';

    q.options.forEach((opt, optIndex) => {
      const choiceDiv = document.createElement('div');
      choiceDiv.className = 'quiz-choice';
      choiceDiv.dataset.index = optIndex;

      const letter = document.createElement('div');
      letter.className = 'choice-letter';
      letter.textContent = String.fromCharCode(65 + optIndex);
      choiceDiv.appendChild(letter);

      const text = document.createElement('div');
      text.className = 'choice-text';
      text.textContent = opt;
      choiceDiv.appendChild(text);

      choicesDiv.appendChild(choiceDiv);
    });

    quizCard.appendChild(choicesDiv);
    contentBox.appendChild(quizCard);
  });
}

// MEMORY FLASHCARD RENDERER (V2.5 Compliance)
function renderMemory(slide) {
  console.log('[V2.5] MemoryRenderer: Flashcards with flip animation');

  const contentBox = document.getElementById('content-box');
  contentBox.innerHTML = '';

  const flashcards = slide.flashcards || slide.memory_items || [];
  const container = document.createElement('div');
  container.className = 'flashcard-container';

  flashcards.forEach((card, index) => {
    const cardDiv = document.createElement('div');
    cardDiv.className = 'flashcard';
    cardDiv.id = `flashcard-${index}`;
    cardDiv.dataset.flipped = 'false';

    const front = document.createElement('div');
    front.className = 'flashcard-front';
    front.innerHTML = `<div class="flashcard-title" style="font-size: 1.3em; font-weight: 600;">${sanitizeMarkdown(card.front)}</div>`;

    const back = document.createElement('div');
    back.className = 'flashcard-back';
    back.innerHTML = `<div class="flashcard-mnemonic" style="font-size: 1.1em;">${sanitizeMarkdown(card.back)}</div>`;

    cardDiv.appendChild(front);
    cardDiv.appendChild(back);
    container.appendChild(cardDiv);
  });

  contentBox.appendChild(container);
}

// MEDIA PRELOADING (V2.5 UX Enhancement)
function preloadNextSection(nextIndex) {
  if (nextIndex >= slides.length) return;

  const nextSlide = slides[nextIndex];

  if (nextSlide.video_path) {
    const videoPreloader = document.createElement('video');
    const resolvedPath = resolveMediaPath(nextSlide.video_path, 'video');
    videoPreloader.src = resolvedPath;
    videoPreloader.preload = 'auto';
    videoPreloader.load();
    console.log(`[V2.5] Preloading next video: ${resolvedPath}`);
  }

  if (nextSlide.avatar_video || nextSlide.avatar_video_path) {
    const avatarPath = nextSlide.avatar_video || nextSlide.avatar_video_path;
    const avatarPreloader = document.createElement('video');
    const resolvedPath = resolveMediaPath(avatarPath, 'avatar');
    avatarPreloader.src = resolvedPath;
    avatarPreloader.preload = 'auto';
    avatarPreloader.load();
    console.log(`[V2.5] Preloading next avatar: ${resolvedPath}`);
  }

  if (nextSlide.audio_path) {
    const resolvedPath = resolveMediaPath(nextSlide.audio_path, 'audio');
    const audioPreloader = new Audio(resolvedPath);
    audioPreloader.preload = 'auto';
    audioPreloader.load();
    console.log(`[V2.5] Preloading next audio: ${resolvedPath}`);
  }
}

async function checkMediaExists(path) {
  try {
    const response = await fetch(path, { method: 'HEAD' });
    return response.ok;
  } catch {
    return false;
  }
}

function showMediaGeneratingPlaceholder(type, container) {
  container.innerHTML = `
    <div class="media-generating-placeholder">
      <div class="spinner"></div>
      <div style="font-size: 1.2em; font-weight: 600;">Generating ${type}...</div>
      <div style="font-size: 0.9em; opacity: 0.9;">This may take a few moments</div>
    </div>
  `;
}

// DISPLAY DIRECTIVES PARSER (V2.5 Core)
function parseDisplayDirectives(slide) {
  const directives = [];
  const segments = slide.narration?.segments || [];

  segments.forEach((seg, i) => {
    if (seg.display_directives) {
      directives.push({
        time: seg.start_time_sec || 0,
        action: seg.display_directives.action_type,
        data: seg.display_directives
      });
    }
  });

  if (slide.flip_timing_sec) {
    directives.push({
      time: slide.flip_timing_sec,
      action: 'show_video',
      data: {}
    });
  }

  return directives.sort((a, b) => a.time - b.time);
}

function renderVisualContent(vc, container) {
  const contentType = vc.content_type || 'paragraph';

  // V2.5 POINTER RESOLUTION
  if (vc.markdown_pointer) {
    const resolvedText = resolvePointer(vc.markdown_pointer);
    if (resolvedText) {
      const block = document.createElement('div');
      // Use a special class for directed content if needed, basically paragraph-block
      block.className = 'paragraph-block pointer-content';
      block.innerHTML = sanitizeMarkdown(resolvedText);
      container.appendChild(block);
      return; // Skip legacy rendering if pointer worked
    } else {
      console.warn("[V2.5] Pointer resolution failed, falling back to legacy fields");
    }
  }

  const verbatimText = vc.verbatim_text || vc.verbatim_content;
  if (verbatimText) {
    const para = document.createElement('div');
    para.className = 'paragraph-block';
    para.innerHTML = sanitizeMarkdown(verbatimText);
    container.appendChild(para);
  }

  const bulletData = vc.bullet_points || vc.items || [];
  if (bulletData.length > 0) {
    const list = document.createElement('ul');
    list.className = 'bullet-list';

    const filteredBullets = bulletData.filter(bp => {
      const text = (typeof bp === 'string' ? bp : (bp.text || '')).trim().toLowerCase();
      return text !== 'thinking...' && text !== 'thinking';
    });

    filteredBullets.forEach(bp => {
      const item = document.createElement('li');
      item.className = 'bullet-item';
      if (bp.level && bp.level > 1) {
        item.classList.add(`level - ${bp.level} `);
      }

      const markers = ['•', '○', '◦', '◇'];
      const level = bp.level || 1;
      const marker = markers[Math.min(level - 1, markers.length - 1)];

      item.innerHTML = `
  < span class="bullet-marker" > ${marker}</span >
    <span class="bullet-text">${sanitizeMarkdown(bp.text || bp)}</span>
`;
      list.appendChild(item);
    });

    if (filteredBullets.length > 0) {
      container.appendChild(list);
    }
  }

  if (vc.ordered_list && vc.ordered_list.length > 0) {
    const list = document.createElement('ol');
    list.className = 'ordered-list';

    vc.ordered_list.forEach((text, i) => {
      const item = document.createElement('li');
      item.className = 'ordered-item';
      item.innerHTML = `
  < span class="ordered-number" > ${i + 1}.</span >
    <span>${sanitizeMarkdown(text)}</span>
`;
      list.appendChild(item);
    });

    container.appendChild(list);
  }

  if (vc.formula || vc.formulas) {
    const formulas = vc.formulas || [vc.formula];
    formulas.forEach(f => {
      const block = document.createElement('div');
      block.className = 'formula-block';
      block.innerHTML = f;
      container.appendChild(block);
    });
  }

  // Handle image display (check content_type or explicit image path fields)
  const imagePath = vc.image || vc.image_path || vc.img || vc.figure || vc.diagram;
  const isImageType = contentType === 'image' || contentType === 'diagram';

  if (imagePath || isImageType) {
    const imgContainer = document.createElement('div');
    imgContainer.className = 'image-container';

    const actualPath = imagePath || vc.image_path;
    if (actualPath) {
      const img = document.createElement('img');
      img.className = 'content-image';
      img.src = resolveMediaPath(actualPath, 'image');
      img.alt = vc.image_caption || vc.caption || vc.verbatim_content || 'Content image';
      img.onerror = () => {
        console.warn(`[V2] Image failed to load: ${actualPath} `);
        imgContainer.style.display = 'none';
      };
      img.onload = () => {
        console.log(`[V2] Image loaded successfully: ${actualPath} `);
      };

      imgContainer.appendChild(img);

      // Add caption if provided (use verbatim_content as fallback for image descriptions)
      const captionText = vc.image_caption || vc.caption || vc.verbatim_content;
      if (captionText) {
        const caption = document.createElement('div');
        caption.className = 'image-caption';
        caption.textContent = captionText;
        imgContainer.appendChild(caption);
      }

      container.appendChild(imgContainer);
    }
  }
}

// [LEGACY RENDERERS REMOVED]
// V2.5 renderQuiz and renderMemory are defined earlier in this file.

// Beat video playlist state for recap sections
let beatVideoPlaylist = [];
let currentBeatIndex = 0;

function renderRecap(slide) {
  console.log('[V2] RecapRenderer: Video focus with beat playlist');

  beatVideoPlaylist = buildBeatPlaylistWithTiming(slide);
  currentBeatIndex = -1;

  if (beatVideoPlaylist.length > 0) {
    console.log(`[V2] Recap beat playlist: ${beatVideoPlaylist.length} videos with timing`);
    beatVideoPlaylist.forEach((b, i) => {
      console.log(`  Scene ${i + 1}: ${b.videoPath} (${b.startTime.toFixed(1)} s - ${b.endTime.toFixed(1)}s)`);
    });
    videoLayer.classList.remove('hidden');
    contentLayer.classList.add('video-mode');
    loadBeatVideo(0);
  } else {
    renderContent(slide);
  }
}

function parseSegmentId(segmentId) {
  if (typeof segmentId === 'number') return segmentId;
  if (typeof segmentId === 'string') {
    const match = segmentId.match(/(\d+)/);
    return match ? parseInt(match[1], 10) : 1;
  }
  return 1;
}

function getSegmentStartTime(segments, segmentId) {
  const idx = parseSegmentId(segmentId) - 1;
  let startTime = 0;
  for (let i = 0; i < idx && i < segments.length; i++) {
    startTime += segments[i].duration_seconds || 5;
  }
  return startTime;
}

function getSegmentEndTime(segments, segmentId) {
  const idx = parseSegmentId(segmentId) - 1;
  let endTime = 0;
  for (let i = 0; i <= idx && i < segments.length; i++) {
    endTime += segments[i].duration_seconds || 5;
  }
  return endTime;
}

function buildBeatPlaylistWithTiming(slide) {
  const segments = slide.narration?.segments || [];
  const visualBeats = slide.visual_beats || [];
  const beatVideoPaths = slide.beat_video_paths || [];
  const recapVideoPaths = slide.recap_video_paths || [];

  const playlist = [];

  if (recapVideoPaths.length > 0) {
    recapVideoPaths.forEach((videoPath, i) => {
      const segIdx = i < segments.length ? i : segments.length - 1;
      playlist.push({
        videoPath: videoPath,
        segmentIndex: segIdx,
        startTime: getSegmentStartTime(segments, segIdx + 1),
        endTime: getSegmentEndTime(segments, segIdx + 1)
      });
    });
    console.log(`[V2] Built recap playlist: ${playlist.length} videos with timing`);
    return playlist;
  }

  if (beatVideoPaths.length > 0 && visualBeats.length > 0) {
    let videoIdx = 0;
    visualBeats.forEach((beat) => {
      if (beat.visual_beat_type === 'video' && videoIdx < beatVideoPaths.length) {
        const segId = beat.segment_id;
        const segIdx = parseSegmentId(segId) - 1;
        playlist.push({
          videoPath: beatVideoPaths[videoIdx],
          segmentIndex: segIdx,
          startTime: getSegmentStartTime(segments, segId),
          endTime: getSegmentEndTime(segments, segId)
        });
        videoIdx++;
      }
    });
    console.log(`[V2] Built content beat playlist: ${playlist.length} videos with timing`);
    return playlist;
  }

  const singleVideo = slide.content_video_path || slide.video_path;
  if (singleVideo) {
    const totalDur = segments.reduce((sum, s) => sum + (s.duration_seconds || 5), 0) || 30;
    playlist.push({
      videoPath: singleVideo,
      segmentIndex: 0,
      startTime: 0,
      endTime: totalDur,
      loop: true
    });
  }

  return playlist;
}

function loadBeatVideo(index) {
  if (index >= beatVideoPlaylist.length) {
    console.log('[V2] All beat videos completed');
    return;
  }

  if (currentBeatIndex === index && contentVideo.src.includes(beatVideoPlaylist[index].videoPath.split('/').pop())) {
    return;
  }

  currentBeatIndex = index;
  const beat = beatVideoPlaylist[index];
  const fullPath = resolveMediaPath(beat.videoPath, 'video');
  console.log(`[V2] Loading beat video ${index + 1}/${beatVideoPlaylist.length}: ${fullPath} (${beat.startTime.toFixed(1)}s - ${beat.endTime.toFixed(1)}s)`);

  contentVideo.muted = true;
  contentVideo.loop = beat.loop || false;
  contentVideo.playsInline = true;
  contentVideo.src = fullPath;
  contentVideo.load();
  contentVideo.playbackRate = 1.0;

  contentVideo.onloadeddata = () => {
    console.log(`[V2] Beat video loaded: ${fullPath}`);
    if (isPlaying) {
      contentVideo.play().catch(e => console.warn('[V2] Beat video play failed:', e));
    }
  };

  contentVideo.onended = () => {
    if (!beat.loop && isPlaying) {
      contentVideo.currentTime = 0;
      contentVideo.play().catch(() => { });
    }
  };
}

function syncBeatVideoToAudio(currentTime) {
  if (beatVideoPlaylist.length === 0) return;

  for (let i = 0; i < beatVideoPlaylist.length; i++) {
    const beat = beatVideoPlaylist[i];
    if (currentTime >= beat.startTime && currentTime < beat.endTime) {
      if (currentBeatIndex !== i) {
        console.log(`[V2] Audio at ${currentTime.toFixed(1)}s - switching to beat ${i + 1}`);
        loadBeatVideo(i);
      }
      return;
    }
  }

  if (beatVideoPlaylist.length === 1 && beatVideoPlaylist[0].loop) {
    if (currentBeatIndex !== 0) {
      loadBeatVideo(0);
    }
  }
}

// ============================================
// AUDIO & PLAYBACK
// ============================================
function setupMediaSource(slide) {
  const hasAvatarVideo = !!slide.avatar_video;
  const audioPath = slide.audio_path || '';

  // Reset timer fallback state
  useTimerFallback = false;
  timerFallback.pause();

  if (hasAvatarVideo) {
    console.log('[V2] Using Avatar Video as Time Source');
    activeTimeSource = avatarVideo;

    const fullPath = resolveMediaPath(slide.avatar_video, 'video');
    avatarVideo.src = fullPath;
    avatarVideo.muted = false;
    avatarVideo.loop = false;
    avatarVideo.load();

    // Ensure audio is cleared
    narrationAudio.pause();
    narrationAudio.src = '';
  } else if (audioPath) {
    // Has audio file - use audio as time source
    console.log('[V2] Using Narration Audio as Time Source');
    activeTimeSource = narrationAudio;

    // Reset avatar to idle
    if (!avatarVideo.src.includes('avatar_placeholder') && slide.section_type !== 'intro') {
      avatarVideo.src = AVATAR_URL;
      avatarVideo.muted = true;
      avatarVideo.loop = true;
      avatarVideo.load();
    }

    const fullPath = resolveMediaPath(audioPath, 'audio');
    console.log(`[V2] Loading audio: ${fullPath}`);
    narrationAudio.src = fullPath;
    narrationAudio.load();
  } else {
    // NO MEDIA AVAILABLE - Use timer fallback with WPM-based duration
    console.log('[V2] No audio/avatar available - Using Timer Fallback (WPM-based)');
    useTimerFallback = true;

    // Calculate duration from segments (already has WPM-based estimates)
    const totalDuration = getTotalDuration(slide);
    timerFallback.reset(totalDuration);
    activeTimeSource = timerFallback;

    // Reset avatar to idle placeholder
    if (slide.section_type !== 'intro') {
      avatarVideo.src = AVATAR_URL;
      avatarVideo.muted = true;
      avatarVideo.loop = true;
      avatarVideo.load();
    }

    // Clear audio
    narrationAudio.pause();
    narrationAudio.src = '';

    // Show "Silent Mode" indicator (audio not ready yet)
    showSilentModeIndicator(true);
  }

  // Hide silent mode indicator if we have media
  if (!useTimerFallback) {
    showSilentModeIndicator(false);
  }

  // Bind events to the chosen source
  bindTimeEvents(activeTimeSource);

  updateTimeDisplay(0, getTotalDuration(slide));
}

// Visual indicator for when audio is not available
function showSilentModeIndicator(show) {
  let indicator = document.getElementById('silent-mode-badge');

  if (show) {
    if (!indicator) {
      indicator = document.createElement('div');
      indicator.id = 'silent-mode-badge';
      indicator.innerHTML = '🔇 Silent Mode (Audio generating...)';
      indicator.style.cssText = `
        position: fixed;
        top: 10px;
        right: 10px;
        background: rgba(255, 152, 0, 0.9);
        color: #fff;
        padding: 8px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        z-index: 1000;
        animation: pulse 2s infinite;
      `;
      // Add pulse animation if not exists
      if (!document.getElementById('silent-mode-style')) {
        const style = document.createElement('style');
        style.id = 'silent-mode-style';
        style.textContent = `
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
          }
        `;
        document.head.appendChild(style);
      }
      document.body.appendChild(indicator);
    }
    indicator.style.display = 'block';
  } else if (indicator) {
    indicator.style.display = 'none';
  }
}

function getTotalDuration(slide) {
  if (slide.audio_duration) return slide.audio_duration;

  const segments = slide.narration?.segments || [];
  let total = 0;
  segments.forEach(seg => {
    total += seg.duration_seconds || 5;
  });
  return total || 30;
}

function togglePlay() {
  isPlaying = !isPlaying;

  const iconPlay = btnPlay.querySelector('.icon-play');
  const iconPause = btnPlay.querySelector('.icon-pause');

  if (isPlaying) {
    iconPlay.classList.add('hidden');
    iconPause.classList.remove('hidden');

    if (activeTimeSource) {
      activeTimeSource.play().catch(() => { });
    }

    // If avatar is not the master source (i.e. we are using audio), play avatar idle loop
    if (activeTimeSource !== avatarVideo) {
      avatarVideo.play().catch(() => { });
    }

    // Ensure avatar canvas is visible and placeholder is hidden
    const placeholder = document.getElementById('avatar-placeholder');
    if (placeholder) placeholder.remove();
    if (avatarCanvas) avatarCanvas.style.display = 'block';

    if (!videoLayer.classList.contains('hidden')) {
      contentVideo.play().catch(() => { });
    }
  } else {
    iconPlay.classList.remove('hidden');
    iconPause.classList.add('hidden');

    if (activeTimeSource) activeTimeSource.pause();
    if (activeTimeSource !== avatarVideo) avatarVideo.pause();
    contentVideo.pause();
  }
}

function updateTimeline() {
  const current = getTime();
  const total = getDuration() || 1;
  const percent = (current / total) * 100;

  timelineFill.style.width = `${percent}%`;
  timelineHandle.style.left = `${percent}%`;

  updateTimeDisplay(current, total);
  updateActiveSegment(current);
}

function updateTimeDisplay(current, total) {
  const formatTime = (t) => {
    const m = Math.floor(t / 60);
    const s = Math.floor(t % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  timeDisplay.textContent = `${formatTime(current)} / ${formatTime(total)}`;
}

// Track if display_directives has been applied for current slide (reset on loadSlide)
let displayDirectivesApplied = false;

function updateActiveSegment(currentTime) {
  // Guard against early calls before slides are loaded
  if (!slides || !slides.length || currentSlideIndex < 0) return;

  const slide = slides[currentSlideIndex];
  if (!slide) return;

  const segments = slide.narration?.segments || [];

  let cumulative = 0;
  let activeIndex = 0;

  for (let i = 0; i < segments.length; i++) {
    const duration = segments[i].duration_seconds || 5;
    if (currentTime >= cumulative && currentTime < cumulative + duration) {
      activeIndex = i;

      // Update quiz progressive reveal if this is a quiz slide
      if (slide.section_type === 'quiz') {
        updateQuizProgressiveReveal(i);
      }
      break;
    }
    cumulative += duration;
  }

  // Apply display_directives on segment change OR on first run for initial segment
  const segmentChanged = activeIndex !== currentSegmentIndex;
  const needsInitialApply = !displayDirectivesApplied && segments.length > 0;

  if (segmentChanged || needsInitialApply) {
    const prevSeg = document.getElementById(`seg-${currentSegmentIndex}`);
    if (prevSeg) prevSeg.classList.remove('segment-active');

    const newSeg = document.getElementById(`seg-${activeIndex}`);
    if (newSeg) newSeg.classList.add('segment-active');

    currentSegmentIndex = activeIndex;

    // Calculate progress within the current segment for karaoke subtitles
    const duration = segments[activeIndex]?.duration_seconds || 5;
    const progress = Math.min(1, Math.max(0, (currentTime - cumulative) / duration));

    // V2.5: Enforce strict "Teach -> Show" toggling logic
    enforceTeachShowLogic(slide, segments[activeIndex], activeIndex);

    // Update subtitles
    const currentSeg = segments[activeIndex];
    if (currentSeg && currentSeg.text) {
      updateSubtitleText(currentSeg.text, progress);
    } else {
      updateSubtitleText("", 0);
    }

    displayDirectivesApplied = true;
  }
}

/**
 * enforceTeachShowLogic: Strict V2.5 Director Bible Implementation
 * 
 * Rules:
 * 1. Intro/Summary/Quiz/Memory/Recap: Handled by own renderers.
 * 2. Content/Example:
 *    - TEACH Phase (Segment 1): Display TEXT (Pointer/JSON). Hide Video. Avatar Optional.
 *    - SHOW Phase (Segment 2): Display VIDEO (Full Screen). Hide Text. Avatar Optional.
 */
function enforceTeachShowLogic(slide, segment, segmentIndex) {
  if (!slide || !segment) return;
  const type = slide.section_type || 'content';

  // Only apply to Content and Example sections
  if (type !== 'content' && type !== 'example') return;

  const purpose = (segment.purpose || '').toLowerCase();

  // Rule 1: SHOW Phase (Video Mode)
  // Trigger: Purpose is 'show' OR visual_type is 'video' OR has video path + strict mode
  const isShowPhase = purpose === 'show' ||
    segment.visual_type === 'video' ||
    segment.visual_type === 'manim' ||
    (segment.display_directives?.visual_layer === 'show');

  if (isShowPhase) {
    console.log(`[V2.5] Segment ${segmentIndex}: SHOW Phase (Video Mode)`);
    videoLayer.classList.remove('hidden');
    contentLayer.classList.add('hidden'); // Hide text layer
    if (contentVideo.paused) {
      contentVideo.play().catch(e => console.warn('Video play failed', e));
    }
    return;
  }

  // Rule 2: TEACH Phase (Text Mode)
  // Trigger: Default if not Show Phase.
  console.log(`[V2.5] Segment ${segmentIndex}: TEACH Phase (Text Mode)`);

  videoLayer.classList.add('hidden');
  contentLayer.classList.remove('hidden');

  // V2.5 Pointer Resolution (Dynamic Text Update)
  // If segment has a 'markdown_pointer', we MUST fetch strict text from sourceMarkdown.
  if (segment.markdown_pointer) {
    const strictText = resolvePointer(segment.markdown_pointer);
    if (strictText) {
      // Find the active segment block and update it dynamically? 
      // Or strictly rely on renderContent having pre-rendered it?
      // For V2.5, we often want to highlight or ensure ONLY this text is visible.
      // Implementation: Scroll to or Highight the pre-rendered block.
      const segEl = document.getElementById(`seg-${segmentIndex}`);
      if (segEl) {
        segEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }
}

/**
 * Helper for V2.5 Pointer Resolution
 * Extracts exact text from sourceMarkdown using start/end phrases.
 */
function resolvePointer(pointer) {
  if (!sourceMarkdown || !pointer) return null;

  const start = pointer.start_phrase;
  const end = pointer.end_phrase;

  if (!start || !end) return null;

  const startIndex = sourceMarkdown.indexOf(start);
  if (startIndex === -1) {
    console.warn(`[V2.5] Pointer START not found: "${start.substring(0, 20)}..."`);
    return null;
  }

  const endIndex = sourceMarkdown.indexOf(end, startIndex);
  if (endIndex === -1) {
    console.warn(`[V2.5] Pointer END not found after start: "${end.substring(0, 20)}..."`);
    return null;
  }

  // Extract full text including end phrase
  const extracted = sourceMarkdown.substring(startIndex, endIndex + end.length);
  return extracted;
}

// ============================================
// SUBTITLES SYSTEM
// ============================================
let subtitleContainer = null;
let currentSubtitleText = ""; // Track current text to avoid re-rendering DOM

function setupSubtitleContainer() {
  if (document.getElementById('subtitle-overlay')) return;

  subtitleContainer = document.createElement('div');
  subtitleContainer.id = 'subtitle-overlay';
  subtitleContainer.style.cssText = `
    position: fixed;
    bottom: 20px;
    left: 0;
    right: 0;
    text-align: center;
    pointer-events: none;
    z-index: 50;
    font-family: 'Inter', sans-serif;
    color: rgba(255, 255, 255, 0.6);
    font-size: 1.2em;
    font-weight: 500;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
    background: transparent;
    padding: 8px 40px;
    transition: opacity 0.3s ease;
    opacity: 0;
    line-height: 1.5;
  `;

  // Add CSS for highlighted words
  const style = document.createElement('style');
  style.textContent = `
    .sub-word {
      display: inline-block;
      white-space: pre;
      margin: 0 2px;
      transition: color 0.05s ease-out, text-shadow 0.05s ease-out;
    }
    .sub-word.played {
      color: #ffffff !important;
      text-shadow: 0 0 10px rgba(255, 255, 255, 0.8), 0 0 20px rgba(255, 255, 255, 0.4);
      transform: scale(1.05);
    }
  `;
  document.head.appendChild(style);

  document.getElementById('stage').appendChild(subtitleContainer);
}

function updateSubtitleText(text, progress) {
  if (!subtitleContainer) setupSubtitleContainer();

  if (!text || !text.trim()) {
    subtitleContainer.style.opacity = '0';
    currentSubtitleText = "";
    return;
  }

  const cleanText = text.replace(/[*_#\[\]]/g, '').trim();

  // If new text, rebuild DOM
  if (cleanText !== currentSubtitleText) {
    currentSubtitleText = cleanText;
    const words = cleanText.split(/\s+/);
    subtitleContainer.innerHTML = ''; // Clear
    words.forEach((w, i) => {
      const span = document.createElement('span');
      span.textContent = w;
      span.className = 'sub-word';
      span.id = `sub-w-${i}`;
      subtitleContainer.appendChild(span);
    });
    subtitleContainer.style.opacity = '1';
  }

  // Update highlighting based on progress
  if (subtitleContainer.children.length > 0) {
    const totalWords = subtitleContainer.children.length;
    // Simple linear interpolation: which word index are we at?
    const activeIndex = Math.floor(progress * totalWords);

    Array.from(subtitleContainer.children).forEach((span, i) => {
      if (i <= activeIndex) {
        span.classList.add('played');
      } else {
        span.classList.remove('played');
      }
    });
  }
}

function seekTimeline(e) {
  const track = e.currentTarget;
  const rect = track.getBoundingClientRect();
  const percent = (e.clientX - rect.left) / rect.width;

  const duration = getDuration();

  if (duration && activeTimeSource) {
    activeTimeSource.currentTime = percent * duration;
    // Reveal all items up to current time when seeking
    const currentTime = getTime();

    revealItems.forEach(item => {
      if (currentTime >= item.revealAt && !item.revealed) {
        item.element.classList.remove('reveal-hidden');
        item.element.classList.add('reveal-visible');
        item.revealed = true;
      }
    });
  }
}

function onSlideEnd() {
  if (currentSlideIndex < slides.length - 1) {
    setTimeout(() => {
      loadSlide(currentSlideIndex + 1);
      // Auto-play if we were playing
      if (isPlaying) {
        startPlayback();
      }
    }, 500);
  } else {
    isPlaying = false;
    btnPlay.querySelector('.icon-play').classList.remove('hidden');
    btnPlay.querySelector('.icon-pause').classList.add('hidden');
  }
}

function startPlayback() {
  if (activeTimeSource) {
    activeTimeSource.play().catch(() => { });
  }

  if (activeTimeSource !== avatarVideo) {
    avatarVideo.play().catch(() => { });
  }

  if (!videoLayer.classList.contains('hidden')) {
    contentVideo.play().catch(() => { });
  }
}

function onContentVideoEnd() {
  // With audio-synced beat switching, video end just loops the current beat
  // The syncBeatVideoToAudio function handles switching based on narration time

  if (beatVideoPlaylist.length > 0 && currentBeatIndex >= 0) {
    const currentBeat = beatVideoPlaylist[currentBeatIndex];
    const currentAudioTime = getTime();

    // If still within this beat's time window, loop the video
    if (currentBeat && currentAudioTime < currentBeat.endTime && isPlaying) {
      console.log(`[V2] Looping beat ${currentBeatIndex + 1} (audio at ${currentAudioTime.toFixed(1)}s, beat ends at ${currentBeat.endTime.toFixed(1)}s)`);
      contentVideo.currentTime = 0;
      contentVideo.play().catch(() => { });
      return;
    }
  }

  // For single looping videos
  const slide = slides[currentSlideIndex];
  if (slide && beatVideoPlaylist.length === 1 && beatVideoPlaylist[0]?.loop) {
    contentVideo.currentTime = 0;
    contentVideo.play().catch(() => { });
    return;
  }

  // Video ended and we're past all beats, hide video layer
  if ((activeTimeSource && activeTimeSource.ended) || !isPlaying) {
    videoLayer.classList.add('hidden');
    contentLayer.classList.remove('video-mode');
  }
}

// ============================================
// NAVIGATION
// ============================================
function prevSlide() {
  if (currentSlideIndex > 0) {
    loadSlide(currentSlideIndex - 1);
    if (isPlaying) startPlayback();
  }
}

function nextSlide() {
  if (currentSlideIndex < slides.length - 1) {
    loadSlide(currentSlideIndex + 1);
    if (isPlaying) startPlayback();
  }
}

function handleKeyboard(e) {
  switch (e.key) {
    case ' ':
      e.preventDefault();
      togglePlay();
      break;
    case 'ArrowLeft':
      prevSlide();
      break;
    case 'ArrowRight':
      nextSlide();
      break;
    case 'd':
    case 'D':
      toggleDevPanel();
      break;
  }
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => { });
  } else {
    document.exitFullscreen();
  }
}

// ============================================
// PROGRESSIVE REVEAL SYSTEM
// ============================================
function setupProgressiveReveal(slide) {
  // Find all revealable elements (only visible ones, not hidden by content splitting)
  const revealableElements = Array.from(contentBox.querySelectorAll(
    '.summary-item, .bullet-item, .ordered-item, .paragraph-block, .quiz-choice, .flashcard, .segment-block'
  )).filter(el => el.style.display !== 'none');

  if (revealableElements.length === 0) {
    console.log('[V2] No revealable elements found');
    return;
  }

  const totalDuration = getTotalDuration(slide);

  // If no audio or very short duration, reveal all immediately
  if (totalDuration <= 1 || !slide.audio_path) {
    console.log('[V2] Progressive reveal: No audio, showing all items');
    revealableElements.forEach(el => {
      el.classList.remove('reveal-hidden');
      el.classList.add('reveal-visible');
    });
    return;
  }

  const timePerItem = Math.max(0.5, totalDuration / revealableElements.length); // Min 0.5s per item

  revealItems = [];

  revealableElements.forEach((el, index) => {
    el.classList.add('reveal-hidden');
    revealItems.push({
      element: el,
      revealAt: index * timePerItem,
      revealed: false
    });
  });

  console.log(`[V2] Progressive reveal setup: ${revealItems.length} items, ${timePerItem.toFixed(2)}s each`);

  // Reveal first item immediately (so there's always something on screen)
  if (revealItems.length > 0) {
    revealItems[0].element.classList.remove('reveal-hidden');
    revealItems[0].element.classList.add('reveal-visible');
    revealItems[0].revealed = true;
  }
}

function updateProgressiveReveal() {
  if (revealItems.length === 0) return;

  const currentTime = getTime();

  revealItems.forEach(item => {
    if (!item.revealed && currentTime >= item.revealAt) {
      item.element.classList.remove('reveal-hidden');
      item.element.classList.add('reveal-visible');
      item.revealed = true;
    }
  });
}

function revealAllItems() {
  // Reveal all items immediately (for seeking or when audio ends)
  revealItems.forEach(item => {
    item.element.classList.remove('reveal-hidden');
    item.element.classList.add('reveal-visible');
    item.revealed = true;
  });
}

// ============================================
// CONTENT SPLITTING (For Large Content)
// ============================================
let contentPages = [];
let currentPageIndex = 0;

function setupContentSplitting(slide) {
  contentPages = [];
  currentPageIndex = 0;

  // Get all direct children of content box that are content blocks
  const contentElements = Array.from(contentBox.querySelectorAll('.segment-block, .summary-item, .bullet-item, .paragraph-block'));

  if (contentElements.length <= 1) {
    console.log('[V2] Content splitting: Single element, no splitting needed');
    return;
  }

  // Check if content overflows
  if (contentBox.scrollHeight <= contentBox.clientHeight) {
    console.log('[V2] Content splitting: No overflow, no splitting needed');
    return;
  }

  // If no audio, show all content (no splitting without timing)
  if (!slide.audio_path) {
    console.log('[V2] Content splitting: No audio, showing all content');
    return;
  }

  console.log('[V2] Content splitting: Overflow detected, splitting content');

  // Split content into pages based on what fits
  const totalDuration = getTotalDuration(slide);
  const pageBreakpoints = [];
  let currentHeight = 0;
  const maxHeight = contentBox.clientHeight * 0.9; // 90% of container
  let pageStartIndex = 0;

  contentElements.forEach((el, index) => {
    const elHeight = el.offsetHeight + 12; // Include margin

    if (currentHeight + elHeight > maxHeight && index > pageStartIndex) {
      // Start new page
      pageBreakpoints.push({
        startIndex: pageStartIndex,
        endIndex: index - 1
      });
      pageStartIndex = index;
      currentHeight = elHeight;
    } else {
      currentHeight += elHeight;
    }
  });

  // Add final page
  pageBreakpoints.push({
    startIndex: pageStartIndex,
    endIndex: contentElements.length - 1
  });

  if (pageBreakpoints.length <= 1) {
    console.log('[V2] Content splitting: Fits in one page');
    return;
  }

  // Calculate timing for each page
  const timePerPage = totalDuration / pageBreakpoints.length;

  contentPages = pageBreakpoints.map((bp, i) => ({
    elements: contentElements.slice(bp.startIndex, bp.endIndex + 1),
    showAt: i * timePerPage,
    hideAt: (i + 1) * timePerPage,
    active: false
  }));

  console.log(`[V2] Content splitting: ${contentPages.length} pages, ${timePerPage.toFixed(2)}s each`);

  // Initially show only first page
  contentElements.forEach(el => el.style.display = 'none');
  if (contentPages.length > 0) {
    contentPages[0].elements.forEach(el => el.style.display = '');
    contentPages[0].active = true;
    currentPageIndex = 0;
  }
}

function updateContentPages() {
  if (contentPages.length <= 1) return;

  const currentTime = getTime();

  contentPages.forEach((page, index) => {
    const shouldBeVisible = currentTime >= page.showAt && currentTime < page.hideAt;

    if (shouldBeVisible && !page.active) {
      // Show this page
      page.elements.forEach(el => {
        el.style.display = '';
        el.classList.add('fade-in');
      });
      page.active = true;
      currentPageIndex = index;
      console.log(`[V2] Showing content page ${index + 1}/${contentPages.length}`);
    } else if (!shouldBeVisible && page.active && index < contentPages.length - 1) {
      // Hide this page (but keep last page visible)
      page.elements.forEach(el => el.style.display = 'none');
      page.active = false;
    }
  });
}

// Add to timeupdate listener
function handleTimeUpdate() {
  handleTimeUpdateMain();
}

// ============================================
// UTILITIES
// ============================================

/**
 * Typeset LaTeX in an element using MathJax
 * Waits for MathJax to be ready, then processes the element
 */
async function typesetMath(element) {
  if (!element) return;

  try {
    if (window.MathJax) {
      // Wait for MathJax to be ready if startup promise exists
      if (MathJax.startup && MathJax.startup.promise) {
        await MathJax.startup.promise;
      }
      // Typeset the specific element
      await MathJax.typesetPromise([element]);
      console.log('[V2] MathJax typeset complete');
    }
  } catch (err) {
    console.warn('[V2] MathJax typeset error:', err);
  }
}

/**
 * Sanitize markdown while PRESERVING LaTeX expressions
 * LaTeX delimiters: $...$, $$...$$, \(...\), \[...\]
 */
/**
 * Enhanced Markdown Sanitizer with Table & Image Support
 * PRESERVES LaTeX expressions
 */
function sanitizeMarkdown(text) {
  if (!text || typeof text !== 'string') return text;

  // 1. Protect LaTeX expressions
  const latexPatterns = [];
  let placeholderIndex = 0;

  text = text.replace(/\$\$([^$]+)\$\$/g, (match) => { latexPatterns.push(match); return `__LATEX_BLOCK_${placeholderIndex++}__`; });
  text = text.replace(/\$([^$\n]+?)\$/g, (match) => { latexPatterns.push(match); return `__LATEX_INLINE_${placeholderIndex++}__`; });
  text = text.replace(/\\\((.+?)\\\)/g, (match) => { latexPatterns.push(match); return `__LATEX_PAREN_${placeholderIndex++}__`; });
  text = text.replace(/\\\[(.+?)\\\]/g, (match) => { latexPatterns.push(match); return `__LATEX_BRACKET_${placeholderIndex++}__`; });

  // 2. Markdown Images: ![alt](src)
  text = text.replace(/!\[(.*?)\]\((.*?)\)/g, (match, alt, src) => {
    const fullSrc = resolveMediaPath(src, 'image');
    return `<div class="image-container"><img src="${fullSrc}" alt="${alt}" class="content-image" /><div class="image-caption">${alt}</div></div>`;
  });

  // 3. Markdown Tables
  // Matches: | head | head | \n |---|---| \n | cell | cell |
  const tableRegex = /\|(.+)\|\n\s*\|[-:| ]+\|\s*\n((?:\|.*\|\n?)+)/g;
  text = text.replace(tableRegex, (match, headerLine, bodyLines) => {
    const headers = headerLine.split('|').filter(c => c.trim()).map(c => c.trim());
    const headerHtml = '<thead><tr>' + headers.map(h => `<th>${h}</th>`).join('') + '</tr></thead>';

    const rows = bodyLines.trim().split('\n').map(row => {
      const cells = row.split('|').filter(c => c.trim() !== '').map(c => c.trim());
      // Note: Simple split might be fragile with pipes in content, but sufficient for now
      return '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>';
    }).join('');

    return `<div class="table-wrapper"><table class="md-table">${headerHtml}<tbody>${rows}</tbody></table></div>`;
  });

  // 4. Basic Formatting
  text = text
    .replace(/^#{1,6}\s*/gm, '') // Remove headers (rendered semantically elsewhere usually, or just strip)
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/__([^_]+)__/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/_([^_]+)_/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/^>\s*(.+)$/gm, '<blockquote>$1</blockquote>')
    // Link support [text](url)
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
    .trim();

  // 5. Restore LaTeX
  text = text.replace(/__LATEX_(BLOCK|INLINE|PAREN|BRACKET)_(\d+)__/g, (match, type, idx) => {
    return latexPatterns[parseInt(idx)] || match;
  });

  return text;
}

function fitContentToContainer(element, options = {}) {
  const { minScale = 0.65, maxScale = 1.0, step = 0.05 } = options;

  if (!element || !element.parentElement) return;

  const container = element.parentElement;
  let scale = maxScale;

  element.style.fontSize = '';
  element.style.lineHeight = '';

  const checkOverflow = () => {
    return element.scrollHeight > container.clientHeight;
  };

  while (checkOverflow() && scale > minScale) {
    scale -= step;
    element.style.fontSize = `${scale}em`;
    element.style.lineHeight = `${1.4 + (1 - scale) * 0.2}`;
  }

  if (checkOverflow()) {
    element.style.overflowY = 'auto';
  }

  console.log(`[V2] Content scaled to ${(scale * 100).toFixed(0)}%`);
}

// Check if a segment is a "thinking", gesture-only, or pause segment that should be filtered
function isThinkingSegment(seg) {
  const vc = seg.visual_content;

  // Check if this is a pause segment (narration only, no display content)
  if (seg.text && /^\[pause\s+\d+\s*seconds?\]$/i.test(seg.text.trim())) {
    return true;
  }

  if (!vc) return false;

  // Check bullet_points for "Thinking..." text
  if (vc.bullet_points) {
    const bps = Array.isArray(vc.bullet_points) ? vc.bullet_points : [vc.bullet_points];
    for (const bp of bps) {
      const text = typeof bp === 'string' ? bp : (bp.text || '');
      if (text.trim().toLowerCase() === 'thinking...' || text.trim().toLowerCase() === 'thinking') {
        return true;
      }
    }
  }

  // Check if gesture_hint is "thinking" with no real content
  if (seg.gesture_hint === 'thinking') {
    const hasContent = vc.paragraph || vc.ordered_list || vc.formula ||
      (vc.bullet_points && vc.bullet_points.length > 0 &&
        !vc.bullet_points.every(bp => {
          const t = typeof bp === 'string' ? bp : (bp.text || '');
          return t.trim().toLowerCase().startsWith('thinking');
        }));
    if (!hasContent) return true;
  }

  return false;
}

// ============================================
// DEV PANEL FUNCTIONS
// ============================================
function setupDevControls() {
  const avatarScaleSlider = document.getElementById('dev-avatar-scale');
  const chromaSlider = document.getElementById('dev-chroma-threshold');
  const contentWidthSlider = document.getElementById('dev-content-width');

  if (avatarScaleSlider) {
    avatarScaleSlider.addEventListener('input', (e) => {
      const scale = parseFloat(e.target.value);
      avatarCanvas.style.transform = `scale(${scale})`;
    });
  }

  if (chromaSlider) {
    chromaSlider.addEventListener('input', (e) => {
      chromaThreshold = parseInt(e.target.value);
      console.log(`[V2] Chroma threshold set to ${chromaThreshold}`);
    });
  }

  if (contentWidthSlider) {
    contentWidthSlider.addEventListener('input', (e) => {
      const width = parseInt(e.target.value);
      contentLayer.style.width = `${width}%`;
    });
  }
}

function toggleDevPanel() {
  if (devPanel) {
    devPanel.classList.toggle('show');
    devModeEnabled = devPanel.classList.contains('show');
    if (devModeEnabled) {
      updateDevInfo();
    }
  }
}

function updateDevInfo() {
  if (!devModeEnabled || !devPanel) return;

  const slide = slides[currentSlideIndex];
  if (!slide) return;

  const slideInfo = document.getElementById('dev-slide-info');
  const sectionInfo = document.getElementById('dev-section-info');
  const audioInfo = document.getElementById('dev-audio-info');
  const videoInfo = document.getElementById('dev-video-info');
  const segmentsList = document.getElementById('dev-segments');

  if (slideInfo) slideInfo.textContent = `${currentSlideIndex + 1}/${slides.length}`;
  if (sectionInfo) sectionInfo.textContent = slide.section_type || 'unknown';
  if (audioInfo) audioInfo.textContent = slide.audio_path || 'none';
  if (videoInfo) videoInfo.textContent = slide.video_path || 'none';

  // Populate segment list
  if (segmentsList) {
    segmentsList.innerHTML = '';
    const segments = slide.narration?.segments || [];
    segments.forEach((seg, i) => {
      const item = document.createElement('div');
      item.className = 'dev-segment-item' + (i === currentSegmentIndex ? ' active' : '');
      const text = (seg.text || '').substring(0, 40) + (seg.text?.length > 40 ? '...' : '');
      const duration = seg.duration_seconds?.toFixed(1) || '?';
      item.innerHTML = `<strong>Seg ${i + 1}</strong> (${duration}s): ${text}`;
      item.onclick = () => seekToSegment(i);
      segmentsList.appendChild(item);
    });
  }
}

function seekToSegment(segmentIndex) {
  const slide = slides[currentSlideIndex];
  const segments = slide.narration?.segments || [];

  let cumTime = 0;
  for (let i = 0; i < segmentIndex && i < segments.length; i++) {
    cumTime += segments[i].duration_seconds || 5;
  }

  if (activeTimeSource) {
    activeTimeSource.currentTime = cumTime;
  }
}

