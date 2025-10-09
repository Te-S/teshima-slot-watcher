import { fetch } from 'undici';
import cheerio from 'cheerio';
import nodemailer from 'nodemailer';

const TARGET_URL = process.env.TARGET_URL || 'https://benesse-artsite.eventos.tokyo/web/portal/797/event/8483/module/booth/239565/185773';

// Email (SMTP) configuration
const SMTP_HOST = process.env.SMTP_HOST;
const SMTP_PORT = Number(process.env.SMTP_PORT || 587);
const SMTP_USER = process.env.SMTP_USER;
const SMTP_PASS = process.env.SMTP_PASS;
const EMAIL_FROM = process.env.EMAIL_FROM; // e.g., "Watcher <watcher@yourdomain.com>"
const EMAIL_TO = process.env.EMAIL_TO;     // comma-separated list allowed

// Symbols: ○ available, △ few left, × not available, 休/— closed (varies)
const AVAILABLE_MARKS = new Set(['\u25EF', '\u25CB', '\u3007', '○', '◯', '〇']);
const FEW_LEFT_MARKS = new Set(['△']);
const BAD_MARKS = new Set(['×', '✕', '✖']);
const CLOSED_MARKS = new Set(['休', '―', '—', '-', '–']);

function normalize(text) {
  return (text || '').replace(/\s+/g, '').trim();
}

function extractMark($, $el) {
  const t = normalize($el.text());
  if (t) return t;

  const imgs = $el.find('img');
  for (const img of imgs.toArray()) {
    const alt = normalize($(img).attr('alt'));
    const title = normalize($(img).attr('title'));
    if (alt) return alt;
    if (title) return title;
  }

  const aria = normalize($el.attr('aria-label'));
  if (aria) return aria;

  const raw = normalize($el.clone().children().remove().end().text());
  return raw || '';
}

function classifyMark(markRaw) {
  if (!markRaw) return 'unknown';
  const mark = markRaw[0];
  if (AVAILABLE_MARKS.has(mark)) return 'available';
  if (FEW_LEFT_MARKS.has(mark)) return 'few_left';
  if (BAD_MARKS.has(mark)) return 'not_available';
  if (CLOSED_MARKS.has(mark)) return 'closed';
  if (/空|可|余|在|available|avail/i.test(markRaw)) return 'available';
  if (/少|△|few/i.test(markRaw)) return 'few_left';
  if (/満|×|✕|不可|closed|休|sold/i.test(markRaw)) return 'not_available';
  return 'unknown';
}

async function parseCalendar(html) {
  const $ = cheerio.load(html);

  const candidates = [];
  $('table, div, ul').each((_, el) => {
    const $el = $(el);
    const cells = $el.find('td, li, div').filter((_, c) => {
      const text = $(c).text();
      return /\b([12]?\d|3[01])\b/.test(text) || /日|月|火|水|木|金|土/.test(text);
    });
    if (cells.length >= 7) candidates.push($el);
  });

  const results = [];
  const scan = ($scope) => {
    $scope.find('td, li, div').each((_, node) => {
      const $cell = $(node);
      const dayText = $cell.text().match(/\b([1-9]|[12]\d|3[01])\b/);
      if (!dayText) return;

      let mark = '';
      const statusEl = $cell.find('span, small, b, strong, img').first();
      if (statusEl.length) {
        mark = extractMark($, statusEl);
      } else {
        const text = normalize($cell.text()).replace(dayText[0], '');
        mark = text;
      }

      const kind = classifyMark(mark);
      if (kind === 'available' || kind === 'few_left') {
        const monthCtx = $cell.closest('table, section, div').prev().text() || '';
        const monthLabel = (monthCtx.match(/(\d{4}).?(\d{1,2})/) || [])[0] || '';
        results.push({
          day: Number(dayText[0]),
          mark,
          kind,
          label: monthLabel || ''
        });
      }
    });
  };

  if (candidates.length) {
    for (const c of candidates) scan(c);
  } else {
    scan($('body'));
  }

  return results;
}

async function notifyEmail(subject, text) {
  if (!SMTP_HOST || !SMTP_PORT || !SMTP_USER || !SMTP_PASS || !EMAIL_FROM || !EMAIL_TO) {
    console.log('EMAIL not configured; message:', subject, text);
    return;
  }

  const transporter = nodemailer.createTransport({
    host: SMTP_HOST,
    port: SMTP_PORT,
    secure: SMTP_PORT === 465,
    auth: { user: SMTP_USER, pass: SMTP_PASS }
  });

  await transporter.sendMail({ from: EMAIL_FROM, to: EMAIL_TO, subject, text });
}

function buildMessage(findings) {
  const lines = findings.map(f => `• ${f.label ? `${f.label} ` : ''}${f.day}: ${f.kind} (${f.mark})`);
  return [
    'Availability detected for Benesse Art Site:',
    ...lines,
    '',
    `Link: ${TARGET_URL}`
  ].join('\n');
}

async function main() {
  const res = await fetch(TARGET_URL, {
    headers: {
      'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36',
      'accept-language': 'ja,en;q=0.9'
    }
  });

  if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
  const html = await res.text();

  const findings = await parseCalendar(html);

  if (findings.length > 0) {
    const msg = buildMessage(findings);
    await notifyEmail('Benesse Art Site: Availability detected', msg);
    console.log('Notification sent:\n' + msg);
  } else {
    console.log('No availability found at this run.');
  }
}

main().catch(async (e) => {
  console.error(e);
  try {
    await notifyEmail('Slot watcher error', `Error: ${e.message}`);
  } catch (_) {}
  process.exit(1);
});

