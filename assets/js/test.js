/* The LoveQuay citizenship test.
 *
 * Twenty-five questions, four parts, 22 to pass. Everything happens in the
 * browser: the answers are here in this file, the marking is done here, and
 * nothing is sent anywhere. There is no server behind this page and no account
 * attached to it.
 *
 * Which means the obvious thing is true, and the page says so out loud rather
 * than pretending otherwise: anyone who opens this file can read the key. The
 * test is open-book by design — it points you at the safety pages and asks you
 * to have read them — so a key that can be found is not a hole in it. The code
 * at the end is a receipt for having sat it, not a credential, and the page
 * says that too.
 *
 * The code itself is 32 characters of the card alphabet from lqid.js — the
 * 31 Crockford symbols with I, L, O, U and Z left out — drawn straight from
 * the browser's cryptographic random source, so every sitting gets its own.
 *
 * It used to be a SHA-256 over the taker's name and answers, which made the
 * same paper reproduce the same code. The name field has gone, and without it
 * that property turns into a defect rather than a feature: two people who
 * answered identically on the same day would be handed the same code and it
 * would look broken. Random is also the more honest shape, since a derived
 * code implies it encodes something a reader could check, and there is no
 * server here to check it against.
 *
 * Every `why` below is drawn from a page on this site, and `ref` points at it.
 * If the site changes, these change with it, or the test starts lying.
 *
 * The four options are shuffled on every attempt, and that is not decoration.
 * As the questions were written the answer ran C, B, D, A, C, B, D, A all the
 * way to the end — a reader who noticed the cycle around question eight could
 * score 25/25 without having read anything at all, which is the one outcome a
 * safety test cannot allow. Shuffling costs the printed answer key, since
 * letters now differ from one sitting to the next; the marking below reports
 * the answer in full text rather than as a letter, so nothing is lost that
 * mattered. Set SHUFFLE to false to go back to the written order.
 */
(function () {
  'use strict';

  var TOTAL = 25;
  var PASS = 22;                       // 88%
  var SHUFFLE = true;                  // see the note at the top of this file
  var CODE_LEN = 32;
  var STORE = 'lq.test.v1';
  var FALLBACK_ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXY';

  /* ---------------------------------------------------------------- data -- */

  var PARTS = [
    {
      title: 'Know your quay',
      blurb: 'The geography, the measurements and the history of the pier.',
      questions: [
        {
          q: 'Approximately how long is the LoveQuay pier?',
          a: ['150 metres', '250 metres', '400 metres', '600 metres'],
          correct: 2,
          why: 'Four hundred metres, running west out of the Inner Harbour. The swimming is at the far end of it.',
          ref: 'index.html', refLabel: 'The Pier'
        },
        {
          q: 'Approximately how wide is the LoveQuay pier?',
          a: ['3 metres', '6 metres', '12 metres', '15 metres'],
          correct: 1,
          why: 'Six metres. It is a working pier, not a promenade — there is not much room either side of you.',
          ref: 'index.html', refLabel: 'The Pier'
        },
        {
          q: 'Which end of LoveQuay is used for swimming?',
          a: ['The easternmost end', 'The middle of the pier', 'The harbour-facing side', 'The westernmost end'],
          correct: 3,
          why: 'The westernmost end, where you can get in off the edge. The east end is where the LOVE sign is, and where you start walking.',
          ref: 'swim.html#where', refLabel: 'Where to swim'
        },
        {
          q: 'How many safety ladders are located at the swimming end of LoveQuay?',
          a: ['Two', 'One', 'Three', 'Four'],
          correct: 0,
          why: 'Two, flanking the swimming spot: one straight, one angled like a set of stairs.',
          ref: 'swim.html#ladders', refLabel: 'Two ladders, one plan'
        },
        {
          q: 'Approximately how long is the stretch of water normally used by LoveQuay swimmers?',
          a: ['50 metres', '100 metres', '150 metres', '400 metres'],
          correct: 2,
          why: 'Roughly 150 metres along the outer face, near the western end. Either side of it there is boat traffic.',
          ref: 'swim.html#where', refLabel: 'Where to swim'
        },
        {
          q: 'What inspired the name LoveQuay?',
          a: ['A historic ship', 'The LOVE public art installation', 'A swimming competition', 'A nearby restaurant'],
          correct: 1,
          why: 'The LOVE installation at the east end of the quay. You walk west from it to reach the water.',
          ref: 'index.html', refLabel: 'The Pier'
        },
        {
          q: 'Which body of water do LoveQuay swimmers enter?',
          a: ['Lake Erie', 'Lake Huron', 'Georgian Bay', 'Lake Ontario'],
          correct: 3,
          why: 'Lake Ontario, at the mouth of Toronto’s Inner Harbour.',
          ref: 'index.html', refLabel: 'The Pier'
        },
        {
          q: 'What is the street address associated with the entrance to LoveQuay?',
          a: ['3 Stadium Road', '100 Queens Quay West', '955 Lake Shore Boulevard West', '1 Bathurst Street'],
          correct: 0,
          why: '3 Stadium Rd, Toronto. Worth knowing by heart: it is the address you would give an ambulance.',
          ref: 'swim.html#where', refLabel: 'Where to swim'
        }
      ]
    },
    {
      title: 'Swimming safely',
      blurb: 'The precautions that matter at a place nobody supervises.',
      questions: [
        {
          q: 'Are there lifeguards stationed at LoveQuay?',
          a: ['Yes, during summer', 'Yes, on weekends', 'No, there are no lifeguards', 'Yes, during organized swims'],
          correct: 2,
          why: 'No lifeguard, no patrol, and no one whose job it is to notice that you went in and did not come out.',
          ref: 'swim.html', refLabel: 'Before you swim'
        },
        {
          q: 'What should you do before entering the water at LoveQuay?',
          a: ['Check only the air temperature', 'Assess the weather, water conditions, hazards and exit points',
              'Wait until someone else jumps in', 'Check only the water temperature'],
          correct: 1,
          why: 'Wind, chop, water temperature, what is floating against the wall, and which ladder you are getting out by. All of it, every visit.',
          ref: 'swim.html', refLabel: 'Before you swim'
        },
        {
          q: 'What is the recommended arrangement when swimming at LoveQuay?',
          a: ['Swim alone with a mobile phone', 'Swim alone if you are experienced',
              'Swim only when the sun is shining', 'Have a companion on the pier watching you throughout your swim'],
          correct: 3,
          why: 'Someone who stays dry, stays put, and can see you the whole time. A person on the deck is worth more than any piece of equipment.',
          ref: 'swim.html', refLabel: 'Before you swim'
        },
        {
          q: 'Where should LoveQuay swimmers avoid swimming?',
          a: ['The Western Channel and marina entrances', 'Near an accessible exit ladder',
              'Along the usual swimming stretch', 'Close to the outer wall within the usual swimming stretch'],
          correct: 0,
          why: 'The channel south of the quay carries the ferry and everything else in and out of the harbour, and boats cut through the gaps in the wall.',
          ref: 'swim.html#where', refLabel: 'Where to swim'
        },
        {
          q: 'Why should you never assume a boat operator can see you?',
          a: ['Boats always have the right of way', 'Boats cannot change direction',
              'Swimmers can be difficult to spot from a boat', 'Boats only operate at night'],
          correct: 2,
          why: 'A head in chop is close to invisible from a helm, and a boat under way cannot stop the way you imagine it can.',
          ref: 'swim.html#where', refLabel: 'Where to swim'
        },
        {
          q: 'Is there a shallow area at the western end of LoveQuay where swimmers can stand and rest?',
          a: ['Yes, beside the straight ladder', 'No, the water is deep alongside the wall',
              'Yes, during summer', 'Yes, when lake levels are low'],
          correct: 1,
          why: 'There is no shallow end to stand up in. If you are tired, the only rest is a ladder.',
          ref: 'index.html', refLabel: 'The Pier'
        },
        {
          q: 'When should you check your intended exit ladder?',
          a: ['When you become tired', 'After entering the water', 'Only during winter',
              'Before entering the water, on every visit'],
          correct: 3,
          why: 'Getting out is harder than getting in. Know which ladder you are heading for, and check you can reach it, before you are in the water.',
          ref: 'swim.html#ladders', refLabel: 'Two ladders, one plan'
        },
        {
          q: 'What should you do if you discover debris or an obstruction at your intended entry point?',
          a: ['Avoid entering there until it is safe', 'Jump over it',
              'Assume it will move away', 'Enter head-first to investigate'],
          correct: 0,
          why: 'Wind piles things up against the wall, and it changes day to day. Never enter head-first into water you have not checked that day.',
          ref: 'swim.html#hazards', refLabel: 'Known hazards'
        }
      ]
    },
    {
      title: 'Winter and cold water',
      blurb: 'Cold takes your strength and your judgement long before it takes your nerve.',
      questions: [
        {
          q: 'What is cold-water shock?',
          a: ['A mild skin irritation', 'A reaction that only occurs below freezing',
              'A sudden physical response that can cause involuntary gasping and rapid breathing',
              'A condition that only affects inexperienced swimmers'],
          correct: 2,
          why: 'Going in fast when the water is cold triggers an involuntary gasp and a sharp spike in breathing rate. It does not care how fit you are.',
          ref: 'swim.html#hazards', refLabel: 'Known hazards'
        },
        {
          q: 'What is the recommended way to enter cold water when conditions permit swimming?',
          a: ['Dive in head-first', 'Enter gradually and maintain control of your breathing',
              'Jump from the highest available point', 'Enter as quickly as possible'],
          correct: 1,
          why: 'Get in gradually, and never jump in cold if you are on your own.',
          ref: 'swim.html#hazards', refLabel: 'Known hazards'
        },
        {
          q: 'Why can floating ice be particularly dangerous at LoveQuay?',
          a: ['It always sinks to the bottom', 'It makes the water warmer',
              'It only appears at night', 'It can be extremely difficult to see in the water'],
          correct: 3,
          why: 'Ice has a refractive index very close to that of the water around it, so a floating chunk barely bends the light passing through it and barely shows.',
          ref: 'swim.html#winter', refLabel: 'Winter swimming'
        },
        {
          q: 'Which ladder is generally easier to climb with cold hands and tired arms, assuming both are in good condition?',
          a: ['The angled, stair-like ladder', 'The straight vertical ladder',
              'Both are necessarily identical', 'Neither ladder is intended for exiting'],
          correct: 0,
          why: 'The angled one is much easier to use with cold hands and tired arms, which is exactly when you will want it.',
          ref: 'swim.html#ladders', refLabel: 'Two ladders, one plan'
        },
        {
          q: 'When should you end a cold-water swim?',
          a: ['Only when you start shivering uncontrollably', 'When everyone else gets out',
              'Before exhaustion or loss of coordination, within your planned personal limits',
              'After reaching a fixed time record'],
          correct: 2,
          why: 'Know your limit and stay within it. By the time your hands stop working, the decision has already been made for you.',
          ref: 'swim.html#winter', refLabel: 'Winter swimming'
        }
      ]
    },
    {
      title: 'Community and responsibility',
      blurb: 'The pier only stays usable because people look after it.',
      questions: [
        {
          q: 'According to the signage at LoveQuay, is the walkway owned or maintained by the City of Toronto?',
          a: ['Yes, throughout the year', 'No', 'Only during summer', 'Only during special events'],
          correct: 1,
          why: 'The sign reads: Danger — Use at Own Risk. Walkway Not Owned or Maintained by The City of Toronto. That is not boilerplate.',
          ref: 'swim.html', refLabel: 'Use at own risk'
        },
        {
          q: 'What should you do if you discover a damaged ladder, broken concrete or an unsafe section of the pier?',
          a: ['Ignore it', 'Wait for the lifeguard to investigate', 'Assume the City already knows',
              'Warn others, avoid the hazard and report its location'],
          correct: 3,
          why: 'There is no lifeguard and no inspection. Photograph it, say where it is, and tell the people around you before you leave.',
          ref: 'friends.html#contact', refLabel: 'Get in touch'
        },
        {
          q: 'What should you do if you see someone struggling in the water?',
          a: ['Call 911, alert others and offer flotation or reaching assistance from a safe position',
              'Immediately jump into the water after them', 'Wait to see if they recover',
              'Record the incident on your phone'],
          correct: 0,
          why: 'Reach or throw, do not go. Two people in difficulty is the common way one person in difficulty becomes a fatality.',
          ref: 'swim.html', refLabel: 'Before you swim'
        },
        {
          q: 'What does being a LoveQuay citizen mean?',
          a: ['Having exclusive access to the pier', 'Being entitled to swim regardless of conditions',
              'Respecting the water, looking out for others and caring for the pier',
              'Completing a minimum number of swims every year'],
          correct: 2,
          why: 'Keep it beautiful. Take out more than you brought in. Nobody needs anything from anyone to swim here.',
          ref: 'friends.html', refLabel: 'Friends of Love Quay'
        }
      ]
    }
  ];

  /* --------------------------------------------------------------- setup -- */

  var form = document.getElementById('lqTestForm');
  if (!form) return;

  var wrap = document.getElementById('lqTestQuestions');
  var submit = document.getElementById('lqTestSubmit');
  var progress = document.getElementById('lqTestProgress');
  var bar = document.getElementById('lqTestBar');
  var result = document.getElementById('lqTestResult');
  var review = document.getElementById('lqTestReview');
  var retake = document.getElementById('lqTestRetake');

  var flat = [];                        // every question, in order, 0..24
  PARTS.forEach(function (part) {
    part.questions.forEach(function (q) { flat.push(q); });
  });

  /* Two numbering schemes run side by side from here on, and keeping them
   * apart is the whole trick. A *canonical* index is the option's position in
   * the data above and never changes; a *shown* index is where it landed on
   * screen this time. Everything stored or marked is canonical, so a code
   * depends on the answers a person gave and not on the order they happened to
   * see them in. Only the letter printed back to them is a shown index.
   *
   * order[i][shown] === canonical. */
  var order = flat.map(function (q) {
    var ix = q.a.map(function (_, i) { return i; });
    if (!SHUFFLE) return ix;
    for (var i = ix.length - 1; i > 0; i--) {     // Fisher-Yates
      var j = Math.floor(Math.random() * (i + 1));
      var t = ix[i]; ix[i] = ix[j]; ix[j] = t;
    }
    return ix;
  });

  function shownOf(i, canonical) { return order[i].indexOf(canonical); }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  /* ------------------------------------------------------------- render -- */

  var n = 0;
  PARTS.forEach(function (part, pi) {
    var head = el('div', 'quiz-part');
    head.appendChild(el('p', 'eyebrow', 'Part ' + (pi + 1)));
    head.appendChild(el('h2', 'quiz-part__title', part.title));
    head.appendChild(el('p', 'quiz-part__blurb', part.blurb));
    wrap.appendChild(head);

    part.questions.forEach(function (q) {
      var i = n++;
      var set = el('fieldset', 'quiz-q');
      set.id = 'q' + (i + 1);

      var legend = el('legend', 'quiz-q__legend');
      legend.appendChild(el('span', 'quiz-q__num', String(i + 1)));
      legend.appendChild(el('span', 'quiz-q__text', q.q));
      set.appendChild(legend);

      var list = el('div', 'quiz-opts');
      order[i].forEach(function (canonical, shown) {
        var id = 'q' + (i + 1) + 'o' + shown;
        var label = el('label', 'quiz-opt');
        label.setAttribute('for', id);

        var radio = document.createElement('input');
        radio.type = 'radio';
        radio.name = 'q' + (i + 1);
        radio.id = id;
        radio.value = String(canonical);

        label.appendChild(radio);
        label.appendChild(el('span', 'quiz-opt__key', 'ABCD'[shown]));
        label.appendChild(el('span', 'quiz-opt__text', q.a[canonical]));
        list.appendChild(label);
      });
      set.appendChild(list);
      wrap.appendChild(set);
    });
  });

  /* -------------------------------------------------------------- state -- */

  function answers() {
    var out = [];
    for (var i = 0; i < TOTAL; i++) {
      var hit = form.querySelector('input[name="q' + (i + 1) + '"]:checked');
      out.push(hit ? Number(hit.value) : -1);
    }
    return out;
  }

  function answered(list) {
    return list.filter(function (v) { return v >= 0; }).length;
  }

  function tick() {
    var list = answers();
    var done = answered(list);
    progress.textContent = done + ' of ' + TOTAL + ' answered';
    bar.style.width = (done / TOTAL * 100) + '%';
    bar.parentNode.setAttribute('aria-valuenow', String(done));
    save(list);
  }

  /* Progress lives on the device only. A 25-question test on a phone at the
   * water should survive an accidental reload; it should not survive onto
   * anybody else's machine, and it never leaves this one. */
  function save(list) {
    try {
      localStorage.setItem(STORE, JSON.stringify({ a: list }));
    } catch (e) { /* private window, blocked storage: carry on without it */ }
  }

  function restore() {
    var raw;
    try { raw = localStorage.getItem(STORE); } catch (e) { return; }
    if (!raw) return;
    var saved;
    try { saved = JSON.parse(raw); } catch (e) { return; }
    if (!saved || !Array.isArray(saved.a)) return;
    saved.a.forEach(function (v, i) {
      if (v < 0 || i >= TOTAL) return;
      var hit = form.querySelector('#q' + (i + 1) + 'o' + shownOf(i, v));
      if (hit) hit.checked = true;
    });
  }

  function forget() {
    try { localStorage.removeItem(STORE); } catch (e) { /* nothing to do */ }
  }

  form.addEventListener('change', tick);

  /* --------------------------------------------------------------- code -- */

  /* 32 symbols from the 31-character card alphabet. A byte taken modulo 31
   * would be biased, because 256 is not a multiple of 31 and the first eight
   * symbols would come up slightly more often; bytes of 248 and over are
   * thrown away instead and more are drawn until 32 have survived. Same
   * reasoning as the check character in lqid.js, where using a power of two
   * quietly broke the arithmetic.
   *
   * getRandomValues rather than SHA-256: it needs no secure context, so the
   * code still appears on a page opened over plain http or straight off the
   * filesystem, where crypto.subtle is simply absent. */
  function makeCode() {
    var alpha = (window.LQID && window.LQID.ALPHABET) || FALLBACK_ALPHABET;
    var size = alpha.length;
    var limit = 256 - (256 % size);
    var out = '';

    while (out.length < CODE_LEN) {
      var bytes = new Uint8Array(CODE_LEN);
      crypto.getRandomValues(bytes);
      for (var b = 0; b < bytes.length && out.length < CODE_LEN; b++) {
        if (bytes[b] < limit) out += alpha[bytes[b] % size];
      }
    }
    return out;
  }

  function groupCode(code) {
    return code.replace(/(.{8})(?=.)/g, '$1-');
  }

  /* ------------------------------------------------------------ marking -- */

  function markup(list, score, date) {
    var passed = score >= PASS;

    result.className = 'quiz-result is-shown ' + (passed ? 'quiz-result--pass' : 'quiz-result--fail');
    result.innerHTML = '';

    result.appendChild(el('p', 'quiz-result__score', score + ' / ' + TOTAL));
    result.appendChild(el('p', 'quiz-result__head',
      passed ? 'Passed. Welcome, citizen.' : 'Not yet.'));

    if (passed) {
      var intro = el('p', 'quiz-result__body',
        'You needed ' + PASS + '. Here is your citizenship code.');
      result.appendChild(intro);

      var codeBox = el('div', 'quiz-code');
      var codeOut = el('p', 'quiz-code__value', '…');
      codeOut.id = 'lqTestCode';
      codeBox.appendChild(el('p', 'quiz-code__label', 'Citizenship code'));
      codeBox.appendChild(codeOut);

      var meta = el('p', 'quiz-code__meta', date + ' · ' + score + '/' + TOTAL);
      codeBox.appendChild(meta);

      var copy = el('button', 'btn btn-outline-navy btn-sm mt-3', 'Copy the code');
      copy.type = 'button';
      codeBox.appendChild(copy);
      result.appendChild(codeBox);

      if (!window.crypto || !crypto.getRandomValues) {
        codeOut.textContent = 'unavailable';
        result.appendChild(el('p', 'quiz-result__body',
          'This browser has no cryptographic random source, so it cannot make a code. '
          + 'Everything else on this page still works.'));
      } else {
        var code = makeCode();
        codeOut.textContent = groupCode(code);
        copy.addEventListener('click', function () {
          var ok = function () {
            copy.textContent = 'Copied';
            setTimeout(function () { copy.textContent = 'Copy the code'; }, 2000);
          };
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(code).then(ok, function () { copy.textContent = 'Select it by hand'; });
          } else {
            copy.textContent = 'Select it by hand';
          }
        });
      }

      result.appendChild(el('p', 'quiz-result__note',
        'The code is drawn at random on your own device the moment you pass, so it is yours and '
        + 'nobody else will be given it. Write it down now — nothing stores it, and starting the '
        + 'test again produces a different one. It is a receipt for having sat the test: it is '
        + 'not a card, it is not identification, and it entitles you to nothing at the water. '
        + 'Nobody needs anything from anyone to swim here.'));
    } else {
      result.appendChild(el('p', 'quiz-result__body',
        'You need ' + PASS + ' of ' + TOTAL + '. Every question you missed is below, with the '
        + 'answer and where on this site it comes from. Read those, then take it again — '
        + 'there is no limit and no penalty.'));
    }

    /* The review is the point of the exercise. Somebody who got the cold-water
     * question wrong should leave this page knowing the answer, whether or not
     * they passed. */
    review.innerHTML = '';
    review.appendChild(el('h2', 'quiz-review__title', 'Every question, marked'));

    flat.forEach(function (q, i) {
      var got = list[i];
      var right = got === q.correct;
      var row = el('div', 'quiz-review__q' + (right ? '' : ' is-wrong'));

      var head = el('p', 'quiz-review__head');
      head.appendChild(el('span', 'quiz-review__num', String(i + 1)));
      head.appendChild(el('span', 'quiz-review__mark', right ? '✓' : '✗'));
      head.appendChild(el('span', 'quiz-review__text', q.q));
      row.appendChild(head);

      if (!right) {
        row.appendChild(el('p', 'quiz-review__yours',
          got < 0 ? 'You left this one blank.'
                  : 'You answered ' + 'ABCD'[shownOf(i, got)] + '. ' + q.a[got]));
      }
      row.appendChild(el('p', 'quiz-review__right',
        'ABCD'[shownOf(i, q.correct)] + '. ' + q.a[q.correct]));

      var why = el('p', 'quiz-review__why', q.why + ' ');
      var link = el('a', null, q.refLabel);
      link.href = q.ref;
      why.appendChild(link);
      row.appendChild(why);

      review.appendChild(row);
    });

    review.classList.add('is-shown');
  }

  /* --------------------------------------------------------------- flow -- */

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var list = answers();

    if (answered(list) < TOTAL) {
      var first = list.indexOf(-1);
      var set = document.getElementById('q' + (first + 1));
      form.querySelectorAll('.quiz-q.is-missing').forEach(function (s) {
        s.classList.remove('is-missing');
      });
      list.forEach(function (v, i) {
        if (v < 0) document.getElementById('q' + (i + 1)).classList.add('is-missing');
      });
      progress.textContent = (TOTAL - answered(list)) + ' still to answer';
      set.scrollIntoView({ block: 'center', behavior: 'smooth' });
      set.querySelector('input').focus({ preventScroll: true });
      return;
    }

    var score = 0;
    flat.forEach(function (q, i) { if (list[i] === q.correct) score++; });

    var date = new Date().toISOString().slice(0, 10);
    markup(list, score, date);

    /* Lock the answers once they have been marked. The review underneath is a
     * record of this attempt; letting someone keep clicking options would
     * leave it describing a test that no longer matches the one on screen. */
    form.querySelectorAll('.quiz-q').forEach(function (set) { set.disabled = true; });
    progress.hidden = true;
    bar.parentNode.hidden = true;

    submit.hidden = true;
    retake.hidden = false;
    result.scrollIntoView({ block: 'start', behavior: 'smooth' });
  });

  /* Reloading rather than resetting in place, because the options are shuffled
   * once when the page is built: clearing the radios would hand somebody the
   * same test back in the same order, which is the position-memorising the
   * shuffle exists to prevent. */
  retake.addEventListener('click', function () {
    forget();
    window.location.hash = 'lqTestStart';
    window.location.reload();
  });

  restore();
  tick();
}());
