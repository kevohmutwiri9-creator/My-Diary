# TODO - AdSense approval readiness (Google policy: avoid thin/low-value content)

- [x] Identify public routes that are indexed: `/`, `/home`, `/about`, `/features`, `/sample-entries`, `/guides`, `/resources`, `/faq`, `/blog`, `/success-stories`
- [x] Inspect public templates rendered by those routes.
- [x] Fix a markup issue in `app/templates/features.html` where the “Wellness Reports” section contained `<li>` without a wrapping `<ul>`.
- [x] Add a new AdSense-friendly, indexable educational content block near the top of `app/templates/home.html` so the homepage has substantive text for non-logged-in users.
- [ ] (Next) Optionally add similar indexable intro blocks to other public pages (`about`, `features`, `sample-entries`, etc.) if needed after another review attempt.
- [ ] Deploy and request AdSense review again (after verifying ads can be requested).

