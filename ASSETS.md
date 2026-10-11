# Visual assets

- `assets/campus-landscape.png`: original decorative illustration made with
  OpenAI image generation for Air Guardian. Direction: Indian school courtyard,
  rich pixel landscape, azure sky, clouds, trees and city skyline, no text,
  logos or readings. It is not a photo of a real campus.
- `assets/campus-landscape.webp`: optimized version used by the site.
- `assets/campus-air.svg` and `assets/indoor-day.svg`: original vector pixel scenes.
- `assets/logo.svg`: custom A-and-wind shield with animated wind strokes.
- `assets/logo-still.svg`: static equivalent for reduced-motion preferences.
- `assets/school-day.svg`: original vector decision board for the welcome page.
- `assets/kids-air-day.svg`: original vector kite/cloud/book scene for Kids. Neither SVG depicts measured conditions or a real school.

The refreshed logo uses sky blue and cyan; its wind animation and reduced-motion behavior are preserved. The campus landscape appears once on the welcome page. The adult overview uses the vector school-day board. Planner/preparation tools use icons rather than repeating the landscape.

- `assets/kids-reading-v2.webp`: original pixel-style illustration generated with OpenAI image generation for the editorial/friendly refresh. An imagined Indian school library, teacher, children, books and paper planes. Optimized to 1200×800, about 210 KB. It is decorative artwork, not a real school, measurement or activity approval. It appears in the Kids view only. Larger raster illustrations are cached when visited rather than downloaded during shell installation.

The provided hackathon screenshot informed layout, colors and illustration style.
Its logos and images were not copied into the site. Decorative illustrations are
labelled and do not indicate actual air conditions.

Leaflet 1.9.4 is vendored under `assets/vendor/leaflet/`, with its BSD-2-Clause license included. It draws the local coordinate map; no external map tiles are requested.

`kids_experience.js` draws Breezy as an original inline SVG cloud character. Its expression and adjacent icon accompany a written planning message. It is decorative guidance, not a sensor, medical assessment or permission to play outside. Gentle movement respects reduced-motion preferences.
