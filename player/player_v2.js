/**
 * PLAYER V2 - Clean Unified Renderer
 * No legacy code - fresh implementation
 */

// ============================================
// CONFIGURATION
// ============================================
const AVATAR_URL = "/player/assets/avatar_placeholder.mp4";

// Determine job ID from URL parameter
const urlParams = new URLSearchParams(window.location.search);
const JOB_ID = urlParams.get('job');

// Set paths based on whether we have a job ID
const BASE_PATH = JOB_ID ? `/jobs/${JOB_ID}/` : '/player_v2/';
const PRESENTATION_PATH = JOB_ID ? `/jobs/${JOB_ID}/presentation.json` : 'presentation.json';

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
  
  narrationAudio.addEventListener('timeupdate', updateTimeline);
  narrationAudio.addEventListener('timeupdate', updateProgressiveReveal);
  narrationAudio.addEventListener('timeupdate', updateContentPages);
  narrationAudio.addEventListener('ended', onSlideEnd);
  
  narrationAudio.onerror = (e) => {
    console.error('[V2] Audio error:', narrationAudio.error);
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
  
  const slide = slides[index];
  const sectionType = slide.section_type || 'content';
  
  console.log(`[V2] Loading slide ${index + 1}: ${sectionType} - ${slide.title || 'Untitled'}`);
  
  // Stop any playing media first
  narrationAudio.pause();
  narrationAudio.currentTime = 0;
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
      renderRecap(slide);
      break;
    case 'content':
    case 'example':
    default:
      renderContent(slide);
      break;
  }
  
  setupAudio(slide);
  
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
    if (vc?.bullet_points) {
      vc.bullet_points.forEach(bp => {
        const text = (typeof bp === 'string' ? bp : (bp.text || '')).trim();
        // Skip "Thinking..." bullets
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
  
  if (videoPath && (renderer === 'manim' || renderer === 'wan_video' || renderer === 'wan')) {
    console.log(`[V2] ContentRenderer: Manim/Video mode - ${videoPath}`);
    const fullPath = resolveMediaPath(videoPath, 'video');
    console.log(`[V2] Loading content video: ${fullPath}`);
    videoLayer.classList.remove('hidden');
    contentLayer.classList.add('video-mode');
    contentVideo.src = fullPath;
    contentVideo.load();
    contentVideo.playbackRate = 1.0;
    return;
  }
  
  const segments = slide.narration?.segments || [];
  
  if (segments.length === 0) {
    const vc = slide.visual_content;
    if (vc) {
      renderVisualContent(vc, contentBox);
    }
    return;
  }
  
  // Render all segments but skip "Thinking..." and gesture-only segments visually
  // Keep original indices for DOM IDs to maintain alignment with playback
  segments.forEach((seg, i) => {
    // Skip thinking/pause segments but create placeholder to maintain ID alignment
    if (isThinkingSegment(seg)) {
      // Create hidden placeholder to maintain segment index alignment
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

function renderVisualContent(vc, container) {
  const contentType = vc.content_type || 'paragraph';
  
  if (vc.verbatim_text) {
    const para = document.createElement('div');
    para.className = 'paragraph-block';
    para.innerHTML = sanitizeMarkdown(vc.verbatim_text);
    container.appendChild(para);
  }
  
  if (vc.bullet_points && vc.bullet_points.length > 0) {
    const list = document.createElement('ul');
    list.className = 'bullet-list';
    
    // Filter out "Thinking..." bullets
    const filteredBullets = vc.bullet_points.filter(bp => {
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
  
  // Handle image display
  const imagePath = vc.image || vc.image_path || vc.img || vc.figure || vc.diagram;
  if (imagePath) {
    const imgContainer = document.createElement('div');
    imgContainer.className = 'image-container';
    
    const img = document.createElement('img');
    img.className = 'content-image';
    img.src = resolveMediaPath(imagePath, 'image');
    img.alt = vc.image_caption || vc.caption || 'Content image';
    img.onerror = () => {
      console.warn(`[V2] Image failed to load: ${imagePath}`);
      imgContainer.style.display = 'none';
    };
    
    imgContainer.appendChild(img);
    
    // Add caption if provided
    if (vc.image_caption || vc.caption) {
      const caption = document.createElement('div');
      caption.className = 'image-caption';
      caption.textContent = vc.image_caption || vc.caption;
      imgContainer.appendChild(caption);
    }
    
    container.appendChild(imgContainer);
  }
}

function renderQuiz(slide) {
  console.log('[V2] QuizRenderer: Question + choices');
  
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
  console.log('[V2] MemoryRenderer: Flashcards');
  
  const flashcards = slide.visual_content?.flashcards || [];
  
  if (flashcards.length === 0) {
    const segments = slide.narration?.segments || [];
    segments.forEach((seg, i) => {
      const card = document.createElement('div');
      card.className = 'flashcard';
      card.id = `seg-${i}`;
      card.innerHTML = `
        <div class="flashcard-title">${sanitizeMarkdown(seg.text || '')}</div>
      `;
      contentBox.appendChild(card);
    });
    return;
  }
  
  const container = document.createElement('div');
  container.className = 'flashcard-container';
  
  flashcards.forEach((fc, i) => {
    const card = document.createElement('div');
    card.className = 'flashcard';
    card.id = `seg-${i}`;
    card.innerHTML = `
      <div class="flashcard-letter">${fc.letter || ''}</div>
      <div class="flashcard-title">${fc.title || ''}</div>
      ${fc.mnemonic ? `<div class="flashcard-mnemonic">${fc.mnemonic}</div>` : ''}
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
  
  // Build beat video playlist from visual_beats or segments
  beatVideoPlaylist = [];
  currentBeatIndex = 0;
  
  const visualBeats = slide.visual_beats || [];
  const segments = slide.narration?.segments || [];
  
  // Try to build playlist from visual_beats with video_asset
  if (visualBeats.length > 0) {
    visualBeats.forEach((beat, i) => {
      if (beat.video_asset) {
        beatVideoPlaylist.push({
          videoPath: beat.video_asset,
          segmentId: beat.segment_id || i + 1,
          startTime: getSegmentStartTime(segments, beat.segment_id || i + 1)
        });
      }
    });
  }
  
  // If visual_beats don't have video_asset, check for numbered beat files
  if (beatVideoPlaylist.length === 0 && slide.video_path) {
    // Extract base pattern from video_path (e.g., "videos/topic_10_beat_0.mp4")
    const baseMatch = slide.video_path.match(/(.+_beat_)(\d+)(\.mp4)$/);
    if (baseMatch) {
      const basePath = baseMatch[1];
      const ext = baseMatch[3];
      // Try to find how many beat videos exist (assume up to 10)
      for (let i = 0; i < Math.min(segments.length, 10); i++) {
        const beatPath = `${basePath}${i}${ext}`;
        beatVideoPlaylist.push({
          videoPath: beatPath,
          segmentId: i + 1,
          startTime: getSegmentStartTime(segments, i + 1)
        });
      }
      console.log(`[V2] Built beat playlist with ${beatVideoPlaylist.length} videos from pattern`);
    }
  }
  
  // Fallback: single video
  if (beatVideoPlaylist.length === 0) {
    const videoPath = slide.content_video_path || slide.video_path;
    if (videoPath) {
      beatVideoPlaylist.push({
        videoPath: videoPath,
        segmentId: 1,
        startTime: 0
      });
    }
  }
  
  if (beatVideoPlaylist.length > 0) {
    console.log(`[V2] Recap beat playlist: ${beatVideoPlaylist.length} videos`);
    videoLayer.classList.remove('hidden');
    contentLayer.classList.add('video-mode');
    loadBeatVideo(0);
  } else {
    // No video, render as content
    renderContent(slide);
  }
}

function getSegmentStartTime(segments, segmentId) {
  let startTime = 0;
  for (let i = 0; i < segmentId - 1 && i < segments.length; i++) {
    startTime += segments[i].duration_seconds || 5;
  }
  return startTime;
}

function loadBeatVideo(index) {
  if (index >= beatVideoPlaylist.length) {
    console.log('[V2] All beat videos completed');
    videoLayer.classList.add('hidden');
    contentLayer.classList.remove('video-mode');
    return;
  }
  
  currentBeatIndex = index;
  const beat = beatVideoPlaylist[index];
  const fullPath = resolveMediaPath(beat.videoPath, 'video');
  console.log(`[V2] Loading beat video ${index + 1}/${beatVideoPlaylist.length}: ${fullPath}`);
  
  contentVideo.src = fullPath;
  contentVideo.load();
  contentVideo.playbackRate = 1.0;
  
  if (isPlaying) {
    contentVideo.play().catch(() => {});
  }
}

// ============================================
// AUDIO & PLAYBACK
// ============================================
function setupAudio(slide) {
  const audioPath = slide.audio_path || '';
  
  if (audioPath) {
    const fullPath = resolveMediaPath(audioPath, 'audio');
    console.log(`[V2] Loading audio: ${fullPath}`);
    narrationAudio.src = fullPath;
    narrationAudio.load();
  } else {
    narrationAudio.src = '';
  }
  
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
    
    if (narrationAudio.src) {
      narrationAudio.play().catch(() => {});
    }
    avatarVideo.play().catch(() => {});
    
    if (!videoLayer.classList.contains('hidden')) {
      contentVideo.play().catch(() => {});
    }
  } else {
    iconPlay.classList.remove('hidden');
    iconPause.classList.add('hidden');
    
    narrationAudio.pause();
    contentVideo.pause();
  }
}

function updateTimeline() {
  const current = narrationAudio.currentTime;
  const total = narrationAudio.duration || 1;
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

function updateActiveSegment(currentTime) {
  const slide = slides[currentSlideIndex];
  const segments = slide.narration?.segments || [];
  
  let cumulative = 0;
  let activeIndex = 0;
  
  for (let i = 0; i < segments.length; i++) {
    const duration = segments[i].duration_seconds || 5;
    if (currentTime >= cumulative && currentTime < cumulative + duration) {
      activeIndex = i;
      break;
    }
    cumulative += duration;
  }
  
  if (activeIndex !== currentSegmentIndex) {
    const prevSeg = document.getElementById(`seg-${currentSegmentIndex}`);
    if (prevSeg) prevSeg.classList.remove('segment-active');
    
    const newSeg = document.getElementById(`seg-${activeIndex}`);
    if (newSeg) newSeg.classList.add('segment-active');
    
    currentSegmentIndex = activeIndex;
  }
}

function seekTimeline(e) {
  const track = e.currentTarget;
  const rect = track.getBoundingClientRect();
  const percent = (e.clientX - rect.left) / rect.width;
  
  if (narrationAudio.duration) {
    narrationAudio.currentTime = percent * narrationAudio.duration;
    // Reveal all items up to current time when seeking
    revealItems.forEach(item => {
      if (narrationAudio.currentTime >= item.revealAt && !item.revealed) {
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
  if (narrationAudio.src) {
    narrationAudio.play().catch(() => {});
  }
  avatarVideo.play().catch(() => {});
  
  if (!videoLayer.classList.contains('hidden')) {
    contentVideo.play().catch(() => {});
  }
}

function onContentVideoEnd() {
  const slide = slides[currentSlideIndex];
  const sectionType = slide?.section_type || 'content';
  
  // For recap sections with beat playlists
  if (sectionType === 'recap' && beatVideoPlaylist.length > 0) {
    const segments = slide.narration?.segments || [];
    const currentBeat = beatVideoPlaylist[currentBeatIndex];
    
    // ISS-199: Check if narration for this beat is still playing
    // If so, loop the video instead of advancing
    if (currentBeat && segments.length > currentBeatIndex) {
      const segment = segments[currentBeatIndex];
      const segmentDuration = segment?.duration_seconds || 0;
      const segmentStartTime = currentBeat.startTime || 0;
      const segmentEndTime = segmentStartTime + segmentDuration;
      const currentAudioTime = narrationAudio.currentTime || 0;
      
      // If narration for this segment is still playing, loop the video
      if (currentAudioTime < segmentEndTime - 0.5 && !narrationAudio.ended && isPlaying) {
        console.log(`[V2] Looping beat video ${currentBeatIndex + 1} (audio at ${currentAudioTime.toFixed(1)}s, segment ends at ${segmentEndTime.toFixed(1)}s)`);
        contentVideo.currentTime = 0;
        contentVideo.play().catch(() => {});
        return;
      }
    }
    
    // Narration for this beat is done, advance to next beat
    currentBeatIndex++;
    if (currentBeatIndex < beatVideoPlaylist.length) {
      console.log(`[V2] Advancing to beat video ${currentBeatIndex + 1}/${beatVideoPlaylist.length}`);
      loadBeatVideo(currentBeatIndex);
      return;
    }
  }
  
  // Video ended, hide video layer and restore content layer
  videoLayer.classList.add('hidden');
  contentLayer.classList.remove('video-mode');
  
  if (narrationAudio.src && !narrationAudio.ended) {
    narrationAudio.play().catch(() => {});
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
    document.documentElement.requestFullscreen().catch(() => {});
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
  
  const currentTime = narrationAudio.currentTime;
  
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
  
  const currentTime = narrationAudio.currentTime;
  
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
  updateContentPages();
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
  
  if (narrationAudio.duration) {
    narrationAudio.currentTime = cumTime;
  }
}
