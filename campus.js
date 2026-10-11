import {esc, icon} from './ui.js';



const activities = ['PE lesson', 'Walk to school', 'Assembly', 'Outdoor play'];

export const noteTypes = ['Traffic at the gate', 'Visible dust', 'Smoke nearby', 'Indoor air concern', 'Other'];



// Duration is a planning input, not a calculation of pollution dose or a safe limit.

export function plannerText(d, activity, minutes) {

  const duration = Number(minutes);

  const kid = d.state.role === 'student';

  if (!activities.includes(activity) || !Number.isInteger(duration) || duration < 1 || duration > 180) {

    return 'Choose an activity and enter between 1 and 180 minutes.';

  }

  const reading = d.r || {};

  const hasReading = Number.isFinite(reading.aqi) && reading.aqi >= 0 && reading.aqi <= 500 &&

    ['India', 'US'].includes(reading.standard);

  if (!hasReading) {

    return kid

      ? 'We do not have an air update. Ask your teacher what your class should do.'

      : 'A current air-quality update is unavailable. Ask school staff to check conditions before planning this activity, and follow the school’s actual instructions.';

  }

  if (kid) {

    const walk = activity === 'Walk to school';

    const suggestion = d.a?.indoor

      ? walk ? 'Ask an adult to help plan your walk and avoid extra waiting outside.' : 'Ask your teacher about indoor games. An adult should check the room.'

      : d.state.preferences?.caution || reading.aqi > 100

        ? walk ? 'Check the school plan with an adult before your walk.' : 'Ask your teacher about a shorter, gentler activity.'

        : 'Check with your teacher before starting. Follow your usual school plan.';

    const source = d.state.mode === 'demo' ? 'This is a practice suggestion.' : 'This is an estimate.';

    return `${suggestion} Your teacher decides. Keep following your care plan. ${source}`;

  }

  const source = d.state.mode === 'demo'

    ? `Practice suggestion using sample ${reading.standard || 'India'} AQI.`

    : 'This suggestion uses a regional model estimate, not a reading at the school gate.';

  const prefix = `For ${duration} ${duration === 1 ? 'minute' : 'minutes'} of ${activity.toLowerCase()}, `;

  const vigorous = activity === 'PE lesson' || activity === 'Outdoor play';

  const long = duration >= 30;

  const caution = d.state.preferences?.caution === true;

  let suggestion;

  if (d.a?.indoor) {

    suggestion = activity === 'Walk to school'

      ? 'ask an adult to review the journey and reduce unnecessary outdoor waiting. This app cannot identify a cleaner route.'

      : 'discuss an indoor alternative with school staff. Indoor air has not been measured here, so also review the room and the school’s ventilation guidance.';

  } else if (caution || reading.aqi > 100) {

    suggestion = activity === 'Walk to school'

      ? 'check the school notice before leaving and ask an adult about reducing time spent waiting near busy traffic. Route pollution is not measured here.'

      : vigorous || long

        ? 'ask staff to review the length and intensity. A shorter, gentler session or an indoor alternative may fit the school’s plan.'

        : 'keep the session gentle and check the school’s latest activity plan before going outside.';

  } else {

    suggestion = activity === 'Walk to school'

      ? 'review the journey with an adult and check for school updates before leaving. No route is rated for pollution in this app.'

      : 'check with staff about following the usual plan and recheck conditions before the session starts.';

  }

  return `${prefix}${suggestion} Follow existing care plans${caution ? ' and the extra-caution setting' : ''}. ${source} The minutes entered do not establish a safe exposure limit.`;

}



export function dayPlanner(d) {

  const kid = d.state.role === 'student';

  const result = typeof d.state.plannerResult === 'string' ? d.state.plannerResult : '';

  const chosen = d.state.plannerSelection;

  const selection = chosen && activities.includes(chosen.activity) && Number.isInteger(Number(chosen.minutes)) && Number(chosen.minutes) >= 1 && Number(chosen.minutes) <= 180

    ? {activity: chosen.activity, minutes: Number(chosen.minutes)}

    : {activity: 'PE lesson', minutes: 30};

  return `<section class="campus-feature panel planner-feature" aria-labelledby="planner-heading">

    <div class="planner-symbol" aria-hidden="true">${icon("clock")}${icon("plan")}</div>

    <div class="feature-kicker">01 / PLAN AHEAD</div>

    <div class="section-heading"><div><h2 id="planner-heading">${kid ? 'What are we doing today?' : 'An activity, with the air in mind.'}</h2><p class="micro">${kid ? 'An adult can help you try this.' : 'Review an activity before the school day starts.'}</p></div>${icon('clock')}</div>

    <form data-planner-form class="planner-form">

      <label class="field" for="planner-activity">Activity<select name="activity" id="planner-activity" aria-label="Activity">${activities.map(activity => `<option value="${esc(activity)}" ${activity === selection.activity ? 'selected' : ''}>${esc(activity)}</option>`).join('')}</select></label>

      <label class="field" for="planner-minutes">Time outdoors (minutes)<input id="planner-minutes" name="minutes" type="number" inputmode="numeric" min="1" max="180" step="1" value="${esc(selection.minutes)}" required /></label>

      <button class="primary" type="submit">Review this activity ${icon('arrow')}</button>

    </form>

    ${result ? `<div class="planner-result" role="status"><b>${kid ? 'Check with an adult' : 'A suggestion to review'}</b><p>${esc(result)}</p></div>` : `<p class="feature-disclaimer">${kid ? 'Try this with an adult. Your teacher decides what your class will do.' : 'Planning help, not activity clearance. Follow your school’s actual instructions.'}</p>`}

  </section>`;

}



export function familyReminders(d) {

  const kid = d.state.role === 'student';

  const checks = Array.isArray(d.familyChecks) ? d.familyChecks : [];

  const items = kid ? [

    ['Check my school plan', 'Ask a parent or teacher what is planned.'],

    ['Pack my water bottle', 'Get ready for the school day.'],

    ['Ask about a mask reminder', 'A grown-up can help if the school or my care plan calls for one.']

  ] : [

    ['Review the school plan', 'Read the latest notice with your child.'],

    ['Pack a water bottle', 'A simple school-day reminder; water does not prevent pollution exposure.'],

    ['Check whether a mask reminder applies', 'Follow school guidance and any existing care plan; ask an adult about suitability.']

  ];

  return `<section class="campus-feature panel family-feature" aria-labelledby="family-heading">

    <div class="preparation-symbol" aria-hidden="true">${icon("journal")}</div>

    <div class="feature-kicker">02 / BEFORE YOU LEAVE</div>

    <div class="section-heading"><div><h2 id="family-heading">${kid ? 'Ready for my day.' : 'A little preparation helps.'}</h2><p class="micro">${kid ? 'Three things to check with a grown-up.' : 'A checklist for your next school run.'}</p></div>${icon('journal')}</div>

    <div class="family-reminders">${items.map(([title, detail], i) => `<div class="preparation-step"><label class="family-reminder"><input type="checkbox" data-family-check="${i}" ${checks[i] ? 'checked' : ''} /><span><b>${title}</b><small>${detail}</small></span></label>${i===0?`<button class="text-button" data-page="plan">Read the school plan ${icon("arrow")}</button>`:""}</div>`).join('')}</div>

    <p class="feature-disclaimer" data-family-progress>${checks.slice(0, 3).filter(Boolean).length} of 3 checked · saved on this device</p>

  </section>`;

}



function timestamp(note) {

  const value = note.time || note.createdAt;

  if (!value) return 'Time unavailable';

  const date = new Date(value);

  if (!Number.isFinite(date.getTime())) return 'Time unavailable';

  return date.toLocaleString('en-IN', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata'}) + ' IST';

}



export function campusNotes(d) {

  if (d.state.role === 'student') return '';

  const notes = Array.isArray(d.campusNotes) ? d.campusNotes.slice(0, 3) : [];

  return `<section class="campus-feature panel campus-notes-feature" aria-labelledby="campus-notes-heading">

    <div class="feature-kicker">03 / ON THE GROUND</div>

    <div class="section-heading"><div><h2 id="campus-notes-heading">What did you notice near school?</h2><p class="micro">Keep a useful note for the next school-day review.</p></div>${icon('school')}</div>

    <div class="campus-grid"><form data-campus-form class="campus-note-form">

      <label class="field" for="campus-type">Observation<select id="campus-type" name="type" aria-label="Observation">${noteTypes.map(type => `<option value="${esc(type)}">${esc(type)}</option>`).join('')}</select></label>

      <label class="field" for="campus-note">Your note<textarea id="campus-note" name="note" maxlength="240" rows="3" required placeholder="For example: construction dust near the east gate during pickup."></textarea></label>

      <button class="primary" type="submit">Save campus note ${icon('plus')}</button>

      <p class="feature-disclaimer">Saved on this device. Observations are not pollution readings and are not sent to school staff.</p>

    </form><div class="campus-notes-list" aria-label="Recent campus notes">

      ${notes.length ? notes.map(note => `<article class="campus-note"><div><span class="tiny-tag">${esc(note.type)}</span><time>${esc(timestamp(note))}</time></div><p>${esc(note.note)}</p><footer><small>${note.role === 'staff' ? 'Staff view' : 'Parent view'} · local observation</small><button class="text-button" type="button" data-campus-delete="${esc(note.id)}" aria-label="Remove note about ${esc(note.type)}">Remove</button></footer></article>`).join('') : '<div class="empty-state"><h3>No campus notes yet.</h3><p>A short observation can help you remember what to discuss with school staff.</p></div>'}

    </div></div>

  </section>`;

}

