# Design system

The interface borrows Ramp's public visual language so the case study reads as if
it belongs next to the product it is about. Everything below is an approximation
assembled from public brand references. **None of it is official Ramp brand
material, and the project is not affiliated with or endorsed by Ramp.**

## Typography

Ramp's public identity pairs two faces:

| Role | Typeface | What it is |
| --- | --- | --- |
| Interface, body, labels | **Lausanne** | Single-weight neo-grotesque by Nizar Kazan / Weltkern, set tight with positive tracking on small uppercase labels |
| Display headlines | **Burgess** | Contemporary serif, used for editorial moments and oversized numerals |

Both are commercially licensed, so neither is bundled or loaded from a CDN here.
The stacks name them first and degrade to widely available faces with similar
proportions:

```css
--font-ui:      "Lausanne", "Inter", "Helvetica Neue", Helvetica, Arial, sans-serif;
--font-display: "Burgess", "Instrument Serif", "Iowan Old Style", Georgia, serif;
```

On a machine with the licensed fonts installed the app renders in them. Everywhere
else it falls back, which is the correct behaviour for a public repository: a
case study should not ship someone else's licensed typeface.

The one stylistic rule worth stating: the serif is for **headlines and
numerals only**. Oversized serif figures announcing a dollar or hour amount are
the most recognisable thing about Ramp's layouts, and that is where the display
face is used — the metric values and the one large number in the addressable-pool
panel. Everything else is the grotesque.

## Colour

A near-monochrome editorial system with a single acid accent. Ramp uses the
highlighter yellow sparingly, only where money moves, and the restraint is the
point. In this app the accent appears at most once per view: on the addressable
pool, on the ranking-change callout, and on button hover.

| Token | Hex | Role |
| --- | --- | --- |
| `--ink` | `#1C1B17` | Near-black. Dominant brand colour, all primary type |
| `--ink-70` | `#55534C` | Secondary type, chart labels |
| `--ink-40` | `#908D84` | Captions, eyebrow labels, axis titles |
| `--rule` | `#E3E1DA` | Hairlines and table borders |
| `--paper` | `#FFFFFF` | Page ground |
| `--paper-warm` | `#F7F6F3` | Panel and sidebar fill |
| `--lime` | `#E5FE54` | Signature accent. One use per view |
| `--lime-deep` | `#C9E33C` | Accent on light fills, where the lime is too pale |
| `--highlight` | `#E4F222` | Highlighter yellow, live and active states |
| `--flag` | `#B4451F` | Caution. **Not a Ramp colour**, added for the data state that needs to read as a warning |

`--flag` is flagged explicitly because inventing a colour and implying it is
part of someone's brand system would be the kind of quiet inaccuracy this
project is trying to avoid. It marks the statistical power check when a pilot
window is too short, which needed to read as a problem and had nowhere to go in
a two-colour palette.

## Charts

Charts follow the same restraint, which forces a useful discipline: with no
colour to spend, the data has to be arranged so the reader's eye lands on the
right mark without being told.

- **Series colour is a single-hue ink ramp**, five steps from `#1C1B17` to
  `#CFCBC2`. Categorical hues would fight the brand and would also encode
  five root causes as five unrelated things, which they are not.
- **Emphasis by value, not by hue.** In the first-versus-repeat chart the repeat
  bar is ink and the first-occurrence bar is rule grey, because one of them is
  the subject and the other is context.
- **Hairline axes, dashed gridlines, no chart borders.** Defined once in
  `src/theme.py` so every chart inherits them.
- **Legends sit below the plot**, horizontal, square symbols.

The palette and chart defaults live in both `assets/ramp.css` and
`src/theme.py`. They are duplicated deliberately: Streamlit styles the chrome
through CSS and the charts through Python, and a single source would have meant
generating one from the other for nine colour values. The two files name each
other in their docstrings so a change to one is an obvious prompt to change the
other.

## Layout

| Rule | Value |
| --- | --- |
| Spacing step | 8px, all padding a multiple of it |
| Corner radius | 4px. Ramp's surfaces are close to square |
| Panel | `--paper-warm` fill, 1px `--rule` border, 3px left bar in `--lime-deep` or `--flag` when it carries a conclusion |
| Measure | Lede text capped at 54 characters for readability |
| Heading scale | Display headline clamps between 2.1rem and 3.1rem on viewport width |
| Tabs | Underline on the active tab, no pill or box |

## Components

Five classes carry the whole interface, defined in `assets/ramp.css`:

- `.erl-eyebrow` — uppercase tracked label above a heading or metric
- `.erl-lede` — serif standfirst under the title
- `.erl-caption` — small grey text, used for every honesty disclaimer
- `.erl-panel` — bordered panel, with `--accent` and `--flag` variants
- `.erl-big` — oversized serif numeral for the one figure that matters in a view

## Accessibility notes

Ink on paper is roughly 15:1, well past AA. The lime accent is the risk: `#E5FE54`
on white is about 1.4:1 and is never used for text, only as a fill behind ink or
as a 3px rule. Ink on lime is about 11:1, which is why the buttons invert to ink
text on a lime ground on hover rather than the other way round. `--ink-40` on
paper is about 3.2:1, so it is used only at 0.72rem and above for captions, which
is the one place in this system where the brand's preference for pale secondary
type and the contrast guidance are genuinely in tension.

## Sources

Brand characteristics were assembled from Ramp's public marketing site and
published design-system write-ups. Hex values are approximations sampled from
those references, not values taken from a Ramp brand guide, and may not match
Ramp's current specification.
