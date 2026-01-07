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

// Media path resolver - handles audio, video, and image paths
function resolveMediaPath(path, type = 'audio') {
  if (!path) return '';

  // Already absolute path
  if (path.startsWith('/') || path.startsWith('http')) {
    return path;
  }

  // Already has subfolder path
  if (path.includes('/')) {
    return BASE_PATH + path;
  }

  // For audio files, they're in audio/ subfolder
  if (type === 'audio') {
    return BASE_PATH + 'audio/' + path;
  }

  // For videos, they're in videos/ subfolder
  if (type === 'video') {
    return BASE_PATH + 'videos/' + path;
  }

  // For images, they're in images/ subfolder
  if (type === 'image') {
    return BASE_PATH + 'images/' + path;
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
    console.warn('[V2] Audio failed to load. Switching to Browser TTS Fallback.');
    enableBrowserTTSFallback();
  };

  contentVideo.addEventListener('ended', onContentVideoEnd);
  contentVideo.onerror = (e) => {
    console.error('[V2] Content video error:', contentVideo.error);
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
    avatarVideo.play().catch(e => {
      console.log('[V2] Avatar autoplay blocked:', e);
      showAvatarPlaceholder();
    });
  };

  avatarVideo.addEventListener('play', startChromaKeyLoop);

  avatarVideo.src = AVATAR_URL;
  avatarVideo.muted = true;
  avatarVideo.loop = true;
  avatarVideo.playsInline = true;
  avatarVideo.load();
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

function getTime() {
  return activeTimeSource ? activeTimeSource.currentTime : 0;
}

function getDuration() {
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
  updateProgressiveReveal();
  updateContentPages();
  // Sync beat video needs explicit time passing or refactoring
  syncBeatVideoToAudio(getTime());
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

async function loadPresentation() {
  try {
    const response = await fetch(PRESENTATION_PATH);
    lessonData = await response.json();

    // V2.5 Director Mode: Fetch source markdown if pointers are expected
    try {
      const mdResponse = await fetch(SOURCE_MARKDOWN_PATH);
      if (mdResponse.ok) {
        sourceMarkdown = await mdResponse.text();
        console.log(`[V2.5] Source Markdown loaded: ${sourceMarkdown.length} chars`);
      } else {
        console.warn("[V2.5] source_markdown.md not found, pointers will fail.");
      }
    } catch (e) {
      console.warn("[V2.5] Failed to load source_markdown.md", e);
    }

    slides = lessonData.sections || [];

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
  });
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

// ============================================
// SECTION RENDERERS
// ============================================

function renderIntro(slide) {
  console.log('[V2] IntroRenderer: Avatar only, no content');
}

function renderSummary(slide) {
  console.log('[V2] SummaryRenderer: Level-1 bullets with checkmarks');

  const segments = slide.narration?.segments || [];
  const allBullets = [];

  segments.forEach(seg => {
    const vc = seg.visual_content;
    const bulletData = vc?.bullet_points || vc?.items || [];
    if (bulletData.length > 0) {
      bulletData.forEach(bp => {
        const text = (typeof bp === 'string' ? bp : (bp.text || '')).trim();
        if (text.toLowerCase() === 'thinking...' || text.toLowerCase() === 'thinking') {
          return;
        }
        if (!bp.level || bp.level === 1) {
          allBullets.push(sanitizeMarkdown(text));
        }
      });
    }
  });

  if (allBullets.length === 0) {
    contentBox.innerHTML = '<p class="paragraph-block">Summary content</p>';
    return;
  }

  const list = document.createElement('ul');
  list.className = 'summary-list';

  allBullets.forEach((text, i) => {
    const item = document.createElement('li');
    item.className = 'summary-item';
    item.id = `seg-${i}`;
    item.innerHTML = `
      <span class="summary-marker">✓</span>
      <span class="summary-text">${text}</span>
    `;
    list.appendChild(item);
  });

  contentBox.appendChild(list);
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
  if (!isRecap && segments.length > 0) {
    console.log(`[V2] ContentRenderer: Rendering ${segments.length} segments with visual_content`);

    segments.forEach((seg, i) => {
      if (isThinkingSegment(seg)) {
        const placeholder = document.createElement('div');
        placeholder.id = `seg-${i}`;
        placeholder.style.display = 'none';
        contentBox.appendChild(placeholder);
        return;
      }

      const segDiv = document.createElement('div');
      segDiv.className = 'segment-block';
      segDiv.id = `seg-${i}`;

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

  // Now handle video loading (for both content and recap sections)
  // For content sections: video will overlay based on flip_timing_sec
  // For recap sections: video-only mode

  // Multi-beat video mode
  if (hasMultiBeat) {
    console.log(`[V2] ContentRenderer: Multi-beat video mode - ${beatVideoPaths.length} videos`);

    beatVideoPlaylist = buildBeatPlaylistWithTiming(slide);
    currentBeatIndex = -1;

    if (beatVideoPlaylist.length > 0) {
      console.log(`[V2] Content beat playlist built with ${beatVideoPlaylist.length} videos`);
      beatVideoPlaylist.forEach((b, i) => {
        console.log(`  Beat ${i}: ${b.videoPath} (${b.startTime.toFixed(1)}s - ${b.endTime.toFixed(1)}s)`);
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
    console.log(`[V2] ContentRenderer: Single video mode - ${videoPath}`);
    const fullPath = resolveMediaPath(videoPath, 'video');
    console.log(`[V2] Loading content video: ${fullPath}`);

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
      console.log(`[V2] Content video loaded successfully: ${fullPath}`);
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
        item.classList.add(`level-${bp.level}`);
      }

      const markers = ['•', '○', '◦', '◇'];
      const level = bp.level || 1;
      const marker = markers[Math.min(level - 1, markers.length - 1)];

      item.innerHTML = `
        <span class="bullet-marker">${marker}</span>
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
        <span class="ordered-number">${i + 1}.</span>
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
        console.warn(`[V2] Image failed to load: ${actualPath}`);
        imgContainer.style.display = 'none';
      };
      img.onload = () => {
        console.log(`[V2] Image loaded successfully: ${actualPath}`);
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

function renderQuiz(slide) {
  console.log('[V2] QuizRenderer: Question + choices');

  // Reset quiz state when loading a new quiz slide to prevent stale state
  window.currentQuizData = null;

  // ISS-300: First check for quiz_data.questions from V2 generator
  // Pass slide for progressive reveal detection
  if (slide.quiz_data?.questions && slide.quiz_data.questions.length > 0) {
    renderQuizFromQuizData(slide.quiz_data.questions, slide);
    return;
  }

  const segments = slide.narration?.segments || [];
  const quizQuestions = [];

  segments.forEach((seg, segIdx) => {
    const vc = seg.visual_content;
    if (vc?.bullet_points && vc.bullet_points.length > 0) {
      let question = '';
      const choices = [];

      vc.bullet_points.forEach(bp => {
        // Handle both object format {level, text} and plain string format
        const text = typeof bp === 'string' ? bp : (bp.text || '');
        const level = typeof bp === 'object' ? bp.level : null;

        // Detect question (starts with number or "Question")
        const isQuestion = /^(\d+\.|Question\s*\d*:?)/i.test(text.trim());
        // Detect choice (starts with A), B), C), D) or A., B., C., D.)
        const choiceMatch = text.trim().match(/^([A-D])[\)\.]\s*(.+)$/i);

        if (level === 1 || isQuestion) {
          // This is a question
          question = text.replace(/^(\d+\.\s*|Question\s*\d*:\s*)/i, '');
        } else if (level === 2 || choiceMatch) {
          // This is a choice
          if (choiceMatch) {
            choices.push({ letter: choiceMatch[1].toUpperCase(), text: choiceMatch[2] });
          } else {
            choices.push({ letter: String.fromCharCode(65 + choices.length), text: text });
          }
        }
      });

      if (question || choices.length > 0) {
        quizQuestions.push({ question, choices, segIdx });
      }
    }
  });

  // Render all questions

  // Helper for V2.5 Pointer Resolution
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
  quizQuestions.forEach((q, idx) => {
    const card = document.createElement('div');
    card.className = 'quiz-card';
    card.id = `seg-${q.segIdx}`;

    if (q.question) {
      const qDiv = document.createElement('div');
      qDiv.className = 'quiz-question';
      qDiv.innerHTML = sanitizeMarkdown(q.question);
      card.appendChild(qDiv);
    }

    if (q.choices.length > 0) {
      const choicesDiv = document.createElement('div');
      choicesDiv.className = 'quiz-choices';

      q.choices.forEach(c => {
        const choice = document.createElement('div');
        choice.className = 'quiz-choice';
        // Check for [Correct] marker
        let choiceText = c.text;
        let isCorrect = false;
        if (choiceText.includes('[Correct]')) {
          choiceText = choiceText.replace(/\s*\[Correct\]\s*/i, '');
          isCorrect = true;
        }
        choice.innerHTML = `
          <span class="choice-letter${isCorrect ? ' correct' : ''}">${c.letter}</span>
          <span class="choice-text">${sanitizeMarkdown(choiceText)}</span>
        `;
        choicesDiv.appendChild(choice);
      });

      card.appendChild(choicesDiv);
    }

    contentBox.appendChild(card);
  });

  // If no quiz questions found from segments, try slide-level visual_content
  if (quizQuestions.length === 0 && slide.visual_content?.bullet_points) {
    renderQuizFromBullets(slide.visual_content.bullet_points);
  }
}

// ISS-300: Render quiz from V2 generator quiz_data.questions format
// With progressive reveal support: questions hidden until narration reaches them
function renderQuizFromQuizData(questions, slide) {
  console.log('[V2] QuizRenderer: Using quiz_data.questions format', questions.length, 'questions');

  // Check if we have per-question narration segments (V2.1 progressive reveal)
  const segments = slide?.narration?.segments || [];
  const hasProgressiveReveal = segments.some(seg => seg.question_index !== undefined);

  if (hasProgressiveReveal) {
    console.log('[V2] QuizRenderer: Progressive reveal mode enabled');
  } else {
    // Backward compatibility: show all questions and answers immediately for legacy content
    console.log('[V2] QuizRenderer: Legacy mode - all questions visible');
  }

  questions.forEach((q, idx) => {
    const card = document.createElement('div');
    card.className = 'quiz-card';
    card.id = `quiz-${idx}`;

    // In progressive reveal mode, hide questions initially
    // In legacy mode, show everything
    if (hasProgressiveReveal) {
      card.classList.add('quiz-hidden');
    }

    // Question
    const qDiv = document.createElement('div');
    qDiv.className = 'quiz-question';
    qDiv.innerHTML = sanitizeMarkdown(q.question);
    card.appendChild(qDiv);

    // Choices
    if (q.options && q.options.length > 0) {
      const choicesDiv = document.createElement('div');
      choicesDiv.className = 'quiz-choices';

      q.options.forEach((opt, optIdx) => {
        const choice = document.createElement('div');
        choice.className = 'quiz-choice';

        // Parse option text - may be "A) text" or just "text"
        let letter = String.fromCharCode(65 + optIdx);
        let text = opt;
        const match = opt.match(/^([A-D])[\)\.]\s*(.+)$/i);
        if (match) {
          letter = match[1].toUpperCase();
          text = match[2];
        }

        // Check if this is the correct answer
        const isCorrect = q.correct_answer === letter;

        // In legacy mode, show correct marker; in progressive reveal, hide initially
        const showCorrectNow = !hasProgressiveReveal && isCorrect;
        choice.innerHTML = `
          <span class="choice-letter${showCorrectNow ? ' correct' : ''}">${letter}</span>
          <span class="choice-text">${sanitizeMarkdown(text)}</span>
        `;
        choice.dataset.correct = isCorrect;
        choice.dataset.letter = letter;
        if (showCorrectNow) {
          choice.classList.add('correct-revealed');
        }
        choicesDiv.appendChild(choice);
      });

      card.appendChild(choicesDiv);
    }

    // Explanation (shown in legacy mode, hidden in progressive reveal)
    if (q.explanation) {
      const explDiv = document.createElement('div');
      explDiv.className = 'quiz-explanation';
      explDiv.style.display = hasProgressiveReveal ? 'none' : 'block';
      explDiv.innerHTML = `<strong>Explanation:</strong> ${sanitizeMarkdown(q.explanation)}`;
      card.appendChild(explDiv);
    }

    contentBox.appendChild(card);
  });

  // Store quiz data for progressive reveal updates
  if (hasProgressiveReveal) {
    window.currentQuizData = {
      questions: questions,
      revealedQuestions: new Set(),
      revealedAnswers: new Set()
    };
  }
}

// Update quiz display based on current narration segment
function updateQuizProgressiveReveal(segmentIndex) {
  const slide = slides[currentSlideIndex];
  if (slide?.section_type !== 'quiz' || !window.currentQuizData) return;

  const segments = slide.narration?.segments || [];
  const currentSeg = segments[segmentIndex];

  if (!currentSeg || currentSeg.question_index === undefined) return;

  const qIdx = currentSeg.question_index;
  const purpose = currentSeg.purpose || '';
  const card = document.getElementById(`quiz-${qIdx}`);

  if (!card) return;

  // Reveal question when we reach its "introduce" segment
  if (purpose === 'introduce' && !window.currentQuizData.revealedQuestions.has(qIdx)) {
    card.classList.remove('quiz-hidden');
    card.classList.add('quiz-active');
    window.currentQuizData.revealedQuestions.add(qIdx);
    console.log(`[V2] Quiz: Revealed question ${qIdx + 1}`);
  }

  // Reveal answer when we reach its "explain" segment
  if (purpose === 'explain' && !window.currentQuizData.revealedAnswers.has(qIdx)) {
    const question = window.currentQuizData.questions[qIdx];
    const correctAnswer = question?.correct_answer;

    // Highlight correct answer
    const choices = card.querySelectorAll('.quiz-choice');
    choices.forEach(choice => {
      if (choice.dataset.correct === 'true') {
        choice.classList.add('correct-revealed');
        const letterSpan = choice.querySelector('.choice-letter');
        if (letterSpan) letterSpan.classList.add('correct');
      }
    });

    // Show explanation
    const explDiv = card.querySelector('.quiz-explanation');
    if (explDiv) {
      explDiv.style.display = 'block';
    }

    window.currentQuizData.revealedAnswers.add(qIdx);
    console.log(`[V2] Quiz: Revealed answer for question ${qIdx + 1}`);
  }
}

function renderQuizFromBullets(bullets) {
  let question = '';
  const choices = [];

  bullets.forEach(bp => {
    const text = typeof bp === 'string' ? bp : (bp.text || '');
    const choiceMatch = text.trim().match(/^([A-D])[\)\.]\s*(.+)$/i);

    if (/^(\d+\.|Question)/i.test(text.trim())) {
      question = text.replace(/^(\d+\.\s*|Question\s*\d*:\s*)/i, '');
    } else if (choiceMatch) {
      choices.push({ letter: choiceMatch[1].toUpperCase(), text: choiceMatch[2] });
    }
  });

  const card = document.createElement('div');
  card.className = 'quiz-card';

  if (question) {
    const qDiv = document.createElement('div');
    qDiv.className = 'quiz-question';
    qDiv.innerHTML = sanitizeMarkdown(question);
    card.appendChild(qDiv);
  }

  if (choices.length > 0) {
    const choicesDiv = document.createElement('div');
    choicesDiv.className = 'quiz-choices';
    choices.forEach(c => {
      const choice = document.createElement('div');
      choice.className = 'quiz-choice';
      choice.innerHTML = `
        <span class="choice-letter">${c.letter}</span>
        <span class="choice-text">${sanitizeMarkdown(c.text)}</span>
      `;
      choicesDiv.appendChild(choice);
    });
    card.appendChild(choicesDiv);
  }

  contentBox.appendChild(card);
}

function renderMemory(slide) {
  console.log('[V2] MemoryRenderer: Flashcards (V2.5 Bible Aligned)');

  // V2.5 Director Bible: flashcards at top level, NOT inside visual_content
  const flashcards = slide.flashcards || slide.visual_content?.flashcards || [];

  if (flashcards.length === 0) {
    // V2.5 Bible: Memory = Flashcards ONLY, no narration text fallback
    console.warn('[V2] Memory section has no flashcards - showing placeholder');
    const placeholder = document.createElement('div');
    placeholder.className = 'memory-placeholder';
    placeholder.textContent = 'No flashcards available for this section.';
    contentBox.appendChild(placeholder);
    return;
  }

  const container = document.createElement('div');
  container.className = 'flashcard-container';

  // V2.5 Director Bible: flashcards have "front" (Term) and "back" (Mnemonic/Answer)
  flashcards.forEach((fc, i) => {
    const card = document.createElement('div');
    card.className = 'flashcard';
    card.id = `seg-${i}`;
    card.innerHTML = `
      <div class="flashcard-front">${sanitizeMarkdown(fc.front || fc.title || '')}</div>
      <div class="flashcard-back">${sanitizeMarkdown(fc.back || fc.mnemonic || '')}</div>
    `;
    container.appendChild(card);
  });

  contentBox.appendChild(container);

  const firstCard = document.querySelector('.flashcard');
  if (firstCard) firstCard.classList.add('active');
}

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
      console.log(`  Scene ${i + 1}: ${b.videoPath} (${b.startTime.toFixed(1)}s - ${b.endTime.toFixed(1)}s)`);
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
  } else {
    console.log('[V2] Using Narration Audio as Time Source');
    activeTimeSource = narrationAudio;

    // Reset avatar to idle
    // Check if we need to reset src to avoid reloading if already correct
    const placeholderUrl = resolveMediaPath(AVATAR_URL); // Ensure resolved path for comparison
    if (!avatarVideo.src.includes('avatar_placeholder') && slide.section_type !== 'intro') {
      avatarVideo.src = AVATAR_URL;
      avatarVideo.muted = true;
      avatarVideo.loop = true;
      avatarVideo.load();
    }

    // Setup Audio logic (legacy setupAudio content)
    const audioPath = slide.audio_path || '';
    if (audioPath) {
      const fullPath = resolveMediaPath(audioPath, 'audio');
      console.log(`[V2] Loading audio: ${fullPath}`);
      narrationAudio.src = fullPath;
      narrationAudio.load();
    } else {
      // No audio file path found - check if we have text to speak
      // Only use fallback if we actually have text segments
      const hasText = slide.narration?.segments?.length > 0;
      if (hasText) {
        console.warn('[V2] No audio path. Using Browser TTS Fallback.');
        enableBrowserTTSFallback();
        return; // Exit here, fallback handles activeTimeSource
      } else {
        narrationAudio.src = '';
      }
    }
  }

  // Bind events to the chosen source
  bindTimeEvents(activeTimeSource);

  updateTimeDisplay(0, getTotalDuration(slide));
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

    // TEACH → SHOW: Apply display_directives for current segment
    applyDisplayDirectives(slide, segments[activeIndex], activeIndex);
    displayDirectivesApplied = true;
  }
}

/**
 * Apply display_directives for TEACH → SHOW pattern
 * When visual_layer='show', display the video overlay; when 'hide', hide video
 * IMPORTANT: Content layer (text/images) remains visible at all times
 * Only the video layer visibility toggles based on display_directives
 */
function applyDisplayDirectives(slide, segment, segmentIndex) {
  if (!segment || !segment.display_directives) return;

  const dd = segment.display_directives;
  const visualLayer = dd.visual_layer || 'hide';

  // Only apply for content sections with video renderer
  const sectionType = slide.section_type || 'content';
  const renderer = slide.renderer || 'none';
  const beatVideoPaths = slide.beat_video_paths || [];

  // Check all possible video sources (matches renderContent logic)
  const hasVideo = (slide.video_path || slide.content_video_path || beatVideoPaths.length > 0) &&
    (renderer === 'video' || renderer === 'manim' || renderer === 'wan' || renderer === 'wan_video');

  // Only apply TEACH → SHOW for content sections (not intro, summary, quiz, memory, recap)
  if (sectionType === 'content' && hasVideo) {
    if (visualLayer === 'show') {
      // SHOW phase: Display video overlay (FULL SCREEN)
      // Hide content layer to prevent overlap (TEACH -> SHOW exclusivity)
      videoLayer.classList.remove('hidden');
      contentLayer.classList.add('hidden');
      contentVideo.play().catch(() => { });
      console.log(`[V2] Segment ${segmentIndex}: SHOW phase - displaying video overlay (content hidden)`);
    } else {
      // TEACH phase: Hide video overlay, content becomes visible again
      videoLayer.classList.add('hidden');
      contentLayer.classList.remove('hidden');
      console.log(`[V2] Segment ${segmentIndex}: TEACH phase - video hidden, content visible`);
    }
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
function sanitizeMarkdown(text) {
  if (!text || typeof text !== 'string') return text;

  // First, protect LaTeX expressions by replacing them with placeholders
  const latexPatterns = [];
  let placeholderIndex = 0;

  // Match $$...$$ (block LaTeX)
  text = text.replace(/\$\$([^$]+)\$\$/g, (match) => {
    latexPatterns.push(match);
    return `__LATEX_BLOCK_${placeholderIndex++}__`;
  });

  // Match $...$ (inline LaTeX) - careful not to match $$ or empty $
  text = text.replace(/\$([^$\n]+?)\$/g, (match) => {
    latexPatterns.push(match);
    return `__LATEX_INLINE_${placeholderIndex++}__`;
  });

  // Match \(...\) (inline LaTeX)
  text = text.replace(/\\\((.+?)\\\)/g, (match) => {
    latexPatterns.push(match);
    return `__LATEX_PAREN_${placeholderIndex++}__`;
  });

  // Match \[...\] (block LaTeX)
  text = text.replace(/\\\[(.+?)\\\]/g, (match) => {
    latexPatterns.push(match);
    return `__LATEX_BRACKET_${placeholderIndex++}__`;
  });

  // Now apply markdown sanitization
  text = text
    .replace(/^#{1,6}\s*/gm, '')           // Remove heading markers at start
    .replace(/\s*#{1,6}\s*$/gm, '')        // Remove heading markers at end
    .replace(/^(.+)\n[=]{2,}\s*$/gm, '$1') // Setext h1
    .replace(/^(.+)\n[-]{2,}\s*$/gm, '$1') // Setext h2
    .replace(/\*\*([^*]+)\*\*/g, '$1')     // Bold **text**
    .replace(/__([^_]+)__/g, '$1')         // Bold __text__
    .replace(/\*([^*]+)\*/g, '$1')         // Italic *text*
    .replace(/_([^_]+)_/g, '$1')           // Italic _text_ (careful with underscores in words)
    .replace(/^>\s*/gm, '')                // Blockquotes
    .replace(/`([^`]+)`/g, '$1')           // Inline code
    .trim();

  // Restore LaTeX expressions
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
// ============================================
// BROWSER TTS FALLBACK (BrowserTTSPlayer)
// ============================================
class BrowserTTSPlayer {
  constructor(slide) {
    this.slide = slide;
    this.segments = slide.narration?.segments || [];
    this.fullText = this.segments.map(s => s.text).join(' ');
    this.duration = slide.audio_duration || (this.fullText.length * 0.08) || 10;
    this.currentTime = 0;
    this.paused = true;
    this.listeners = {};
    this.startTime = 0;
    this.animationFrame = null;

    // Prep synthesis
    this.utterance = new SpeechSynthesisUtterance(this.fullText);
    this.utterance.rate = 1.0;
    this.utterance.onend = () => {
      this.currentTime = this.duration;
      this.dispatchEvent({ type: 'ended' });
      this.pause();
    };
    // Attempt to select a good voice
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v => v.name.includes('Google US English') || v.name.includes('Microsoft Zira'));
    if (preferred) this.utterance.voice = preferred;
  }

  addEventListener(type, callback) {
    if (!this.listeners[type]) this.listeners[type] = [];
    this.listeners[type].push(callback);
  }

  removeEventListener(type, callback) {
    if (!this.listeners[type]) return;
    this.listeners[type] = this.listeners[type].filter(cb => cb !== callback);
  }

  dispatchEvent(event) {
    const list = this.listeners[event.type];
    if (list) list.forEach(cb => cb(event));
  }

  play() {
    if (!this.paused) return Promise.resolve();
    this.paused = false;

    // JS Speech API doesn't support seeking well, so we just speak from start or resume
    // Ideally we would split utterance by segment, but for fallback simplified is okay
    if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
    } else {
      window.speechSynthesis.cancel(); // Reset
      window.speechSynthesis.speak(this.utterance);
    }

    this.lastTick = Date.now();
    this.tick();
    return Promise.resolve();
  }

  pause() {
    this.paused = true;
    window.speechSynthesis.pause();
    if (this.animationFrame) cancelAnimationFrame(this.animationFrame);
  }

  tick() {
    if (this.paused) return;

    const now = Date.now();
    const dt = (now - this.lastTick) / 1000;
    this.lastTick = now;

    this.currentTime += dt;
    if (this.currentTime >= this.duration) {
      this.currentTime = this.duration; // End logic handled by utterance.onend usually, but failsafe
    }

    this.dispatchEvent({ type: 'timeupdate' });

    if (this.currentTime < this.duration) {
      this.animationFrame = requestAnimationFrame(this.tick.bind(this));
    }
  }
}

function enableBrowserTTSFallback() {
  const slide = slides[currentSlideIndex];
  if (!slide) return;

  console.log('[V2] Initializing BrowserTTSPlayer...');

  if (activeTimeSource) {
    unbindTimeEvents(activeTimeSource);
  }

  activeTimeSource = new BrowserTTSPlayer(slide);
  // Important: activeTimeSource must be set BEFORE bindTimeEvents
  bindTimeEvents(activeTimeSource);

  // Show visual cue
  const errDiv = document.createElement('div');
  errDiv.style.cssText = 'position:fixed; top:10px; right:10px; background:rgba(255,193,7,0.8); color:black; padding:5px 10px; border-radius:4px; font-size:12px; z-index:9999; pointer-events:none;';
  errDiv.textContent = 'Using Browser TTS (Fallback)';
  document.body.appendChild(errDiv);
  setTimeout(() => errDiv.remove(), 5000);
}
