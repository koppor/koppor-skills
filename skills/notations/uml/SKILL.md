---
name: uml
description: >-
  Draw and check UML 2.5.1 diagrams (class diagram, object diagram, sequence
  diagram, activity diagram, state machine, use case diagram, communication
  diagram, component diagram, deployment diagram) exactly as the OMG
  specification defines them: arrowheads open or filled, hollow triangles,
  aggregation and composition diamonds, navigability, dashed or solid lines,
  ball and socket, ports, nodes, artifacts. Comes with a notation checklist
  citing the spec clause and figure, TikZ styles for LaTeX, and a python-pptx
  library for native PowerPoint shapes. Use when a slide, deck, .pptx,
  LaTeX/TikZ document, or figure needs a UML diagram, or when a UML diagram
  must be checked for notation errors.
license: MIT
---

# UML 2.5.1 diagrams in TikZ and PowerPoint

UML has many look-alike symbols whose difference is the whole meaning: an open or a
filled arrowhead, a hollow triangle or two strokes, a dashed or a solid line, a diamond at
one end or the other. Agents draw these from memory and get them wrong. This skill has the
notation as a checklist with the clause and figure of the specification for each element,
TikZ styles for LaTeX, and a python-pptx library that draws each element correctly.

## Source of truth

OMG *Unified Modeling Language*, version 2.5.1, formal/17-12-05, December 2017:
<https://www.omg.org/spec/UML/2.5.1/PDF>. In the tables, § is a sub clause and Fig. a
figure of that document; "p." is the page number printed on the page (in the official PDF
the PDF page is the printed page + 42).

**Render the spec figure and compare element by element; do not draw from memory.**
Before calling a diagram done, open the cited figure, enlarge it, and compare each edge
and node of the drawing: head filled or open, number of heads, which end carries the head
or diamond, solid or dashed, angular or rounded corners, bold, italic, or underlined text.

Where a figure and the text disagree, the text wins. Two figures print a dependency head
filled although the text asks for an open one: Fig. 7.18 (generic dependency) and
Fig. 18.3 («extend», "a dashed arrow with an open arrowhead", §18.1.4 p. 642). The other
dependency figures (Fig. 7.20, 10.11, 18.4) and the import, merge, and profile application
notations ("a dashed arrow with an open arrowhead", §7.4.4.3, §12.2.4, §12.3.4) draw it open.
More such figures are listed below the component and the deployment checklist.

## Arrowheads

Three different line ends occur, and they must not be mixed up:

| Line end | Looks like | Used for |
| --- | --- | --- |
| Open head | Two strokes meeting at the tip, nothing between them (`→`) | Navigable association end, dependency (`«use»`, `«include»`, `«extend»`), deployment (`«deploy»`), manifestation (`«manifest»`), activity edge, transition, asynchronous message, reply, create message |
| Filled head | Solid black triangle | Synchronous message (a reply may also use it) |
| Hollow triangle | Closed triangle outline, white inside, larger | Generalization (solid line), realization and component realization (dashed line) |

- **An open head is two strokes, not a hollow triangle.** A hollow triangle on a
  dependency or an association turns it into a realization or generalization.
- **An open head is as narrow as the filled head:** the same length and the same width.
  Do not spread the two strokes wide like a chevron; draw both kinds with one size.
- The hollow triangle and the diamond are separate, larger tips, not line-end variants.
- Diamonds sit at the **whole**, never at the part. Hollow: shared aggregation; filled:
  composite aggregation.

## Notation checklists

### Class diagram

| Element | Drawn as | Typical mistake | Spec (§, Fig.) |
| --- | --- | --- | --- |
| Class | Rectangle; name centred and **bold**, starting upper case; compartments for attributes and operations below, separated by lines. | Name not bold, or compartments drawn as separate boxes. | §9.2.4.1, Fig. 11.16 |
| Abstract class | Name in *italics* (or `{abstract}` below the name). | Keyword «abstract». | §9.2.4.1 |
| Keyword, stereotype | In guillemets `«interface»`, plain face, centred above the name. | `<<interface>>` when `«»` is available; bold keyword. | §9.2.4.1, Annex C |
| Attribute, operation | `visibility name: Type [multiplicity] = default`; `+` public, `-` private, `#` protected, `~` package. Static features are underlined. | Java syntax (`String name`). | §9.5.4, §9.6.4, §9.4.4 p. 110 |
| Association | **Solid** line between the classes. | Dashed line (that is a dependency). | §11.5.4 p. 201, Fig. 11.28 |
| Multiplicity, role name | Near the end they belong to: `1`, `0..1`, `*`, `1..*`; role name at the far end (it becomes the field name). | Multiplicity at the wrong end. | §11.5.4, §7.5.4.1, Fig. 11.28 |
| Navigable end | Open head at that end. Both ends navigable: **two** heads. | Hollow triangle; one head for "both ways". | §11.5.4 p. 202, Fig. 11.29 |
| Not navigable | Small **x** across the line at that end. | Missing x read as "not navigable" (see below). | §11.5.4 p. 202, Fig. 11.29 |
| Dependency | **Dashed** line, **open** head at the supplier; keyword such as `«use»` beside it. | Solid line, filled or hollow-triangle head. | §7.7.4 p. 39, Fig. 7.20, 10.11 |
| Generalization | **Solid** line, **hollow triangle** at the general class. Several may share one triangle. | Open head; triangle at the specific class. | §9.2.4.2 p. 102, Fig. 9.2 |
| Realization, interface realization | **Dashed** line, **hollow triangle** at the interface. | Solid line (generalization); open head (dependency). | §7.7.4 p. 39, §10.4.4, Fig. 10.11 |
| Interface | Class rectangle with `«interface»` above the name, or a ball (provided) and socket (required). | Ball and socket swapped. | §10.4.4, Fig. 10.9-10.11 |
| Shared aggregation | **Hollow** diamond at the **whole**, smaller than an n-ary association diamond. | Diamond at the part. | §11.5.4 p. 202, §9.5.3 |
| Composite aggregation | **Filled** diamond at the **whole**: the part lives and dies with it. | Hollow diamond; used for "object composition" in the GoF sense, where a navigable association is meant. | §11.5.4 p. 202, §9.5.3, Fig. 11.33 |

**Navigability has three presentation options** (§11.5.4, p. 203), chosen for a whole
diagram:

1. Show all arrows and crosses: navigation and its absence are explicit.
2. Suppress all arrows and crosses: nothing can be concluded about navigation.
3. Suppress all crosses, and the arrows of associations navigable both ways; show
   arrows only for one-way navigability. Then two-way navigability looks the same as
   no navigability.

Option 3 is common practice, and it makes a line without heads ambiguous. Recommended
instead, and to be stated once per deck or document: **no head = navigability not
specified** (pair EF in Fig. 11.29), an open head for each navigable end (two heads for
both ways, pair AB), and a small x only where non-navigability matters (pairs CD, GH).
Never read a plain line as "not navigable".

### Object diagram

| Element | Drawn as | Typical mistake | Spec (§, Fig.) |
| --- | --- | --- | --- |
| Object (instance specification) | Rectangle with `name : Type` **underlined**, plain face; `:Type` for an anonymous object. | **Bold** name, no underline (that is a class). | §9.8.4 p. 128, Fig. 9.29-9.32 |
| Slot | `attribute = value` in a compartment below the name. | Type and visibility repeated as in a class. | §9.8.4, Fig. 9.29 |
| Link | Solid line between objects; role names at the ends; arrows only if they agree with the association. | Multiplicities on a link. | §9.8.4, Fig. 9.30 |

### Sequence diagram

| Element | Drawn as | Typical mistake | Spec (§, Fig.) |
| --- | --- | --- | --- |
| Lifeline | Head rectangle with `name:Type` (**not** underlined) and a vertical line, usually dashed ("may be dashed"). An actor may head it as a stick figure. | Underlined head (UML 1 habit). | §17.3.4.1 p. 572, Fig. 17.3, 17.14 |
| Execution specification | Thin white or grey rectangle on the lifeline. | Wide box hiding the messages. | §17.2.4.4 p. 569, Fig. 17.14 |
| Synchronous message | Solid line, **filled** head. | Open head. | §17.4.4.1 p. 577 |
| Asynchronous message | Solid line, **open** head. | Filled head; dashed line. | §17.4.4.1 p. 577 |
| Reply message | **Dashed** line, open (or filled) head, back to the caller. Keep one head style per diagram. | Solid line. | §17.4.4.1 p. 577 |
| Create message | **Dashed** line, open head, ending at the **head** of the new lifeline, which starts lower. | Ending on the dashed line of a lifeline drawn from the top. | §17.4.4.1 p. 577, Fig. 17.14 |
| Combined fragment | Rectangle, operator (`alt`, `opt`, `loop`, `ref`) in a pentagon at the top left; operands separated by a dashed line; guard `[...]` on the lifeline of the first event. | Guard in the pentagon. | §17.6.4, Fig. 17.14 |

> "A synchronous Message (messageSort equals synchCall) has a filled arrow head."
> "An asynchronous Message (messageSort equals asynchCall or asynchSignal) has an open
> arrow head." (§17.4.4.1, p. 577)

### Communication diagram

| Element | Drawn as | Typical mistake | Spec (§, Fig.) |
| --- | --- | --- | --- |
| Lifeline | Rectangle with `name:Type`, not underlined. | Underlined, as in UML 1 collaboration diagrams. | §17.9, Fig. 17.26 |
| Message | Small arrow parallel to the link line, next to `sequence-number: name`; `1a`, `1b` for concurrent, `1.1` for nested. | Arrowhead on the link itself. | §17.4.4.1 p. 577, Fig. 17.26 |

### Activity diagram

| Element | Drawn as | Typical mistake | Spec (§, Fig.) |
| --- | --- | --- | --- |
| Action | Rectangle with **rounded** corners. | Square corners; an ellipse. | §16.2.4.1, Fig. 16.2 |
| Call behavior action | Action with a **rake** (fork-like symbol) inside, lower right. | Missing rake when another activity is called. | §16.3.4.1, Fig. 16.15 |
| Activity edge | Solid line, **open** head. Guards `[...]` near the source. | Filled head; guard without brackets. | §15.2.4 p. 380, Fig. 15.5 |
| Initial node | Small filled circle. | Hollow circle. | §15.3.4.1, Fig. 15.27 |
| Activity final node | Circle around a filled circle ("bull's eye"): **ends the whole activity**. | Used where only one branch ends. | §15.3.4.1, Fig. 15.28 |
| Flow final node | Circle with an **X**: ends **this flow only**. | Confused with the activity final node. | §15.3.4.1, Fig. 15.28 |
| Decision, merge | Hollow diamond; one way out, guards on the outgoing edges. Merge does not wait. | Bar used for a decision. | §15.3.4.3, Fig. 15.32, 15.33 |
| Fork, join | Filled bar; all ways in parallel, join waits for all. | Diamond used for parallel flows. | §15.3.4.2, Fig. 15.29 |
| Partition (swimlane) | Two parallel lines, name in a box at one end. | Coloured boxes without lines. | §15.6.4.1, Fig. 15.70 |

### State machine diagram

| Element | Drawn as | Typical mistake | Spec (§, Fig.) |
| --- | --- | --- | --- |
| State | Rectangle with **rounded** corners, name inside; optional compartment with `entry /`, `do /`, `exit /`. | Square corners (that is a class or object). | §14.2.4.4, Fig. 14.4, 14.6 |
| Initial pseudostate | Small filled circle; its transition is unlabeled (only a classifier behavior may name the creating event). | Trigger or guard on the initial transition. | §14.2.4.6 p. 327, Fig. 14.18 |
| Final state | Circle around a filled circle, the same symbol as the activity final node. | Flow final symbol (X). | §14.2.4.5, Fig. 14.17 |
| Transition | Solid line, open head, label `trigger [guard] / effect`, all parts optional. | Filled head; effect before the guard. | §14.2.4.8 |
| Choice pseudostate | Hollow diamond with guarded outgoing transitions. | | §14.2.4.6, Fig. 14.25 |
| Time event | `after` followed by a duration (`after 5 seconds`), or `at` followed by a point in time, as the trigger. | | §13.3.4 |

### Use case diagram

| Element | Drawn as | Typical mistake | Spec (§, Fig.) |
| --- | --- | --- | --- |
| Subject (system boundary) | Rectangle around the use cases, name at the **top left**. | Name centred, or actors inside. | §18.1.4 p. 641 |
| Use case | Ellipse with the name inside (or below). | Rectangle. | §18.1.4 |
| Actor | **Stick figure** with the name below, **or** a class rectangle with the keyword `«actor»`. The rectangle suits other systems, so that they do not look like people. | Stick figure inside the system boundary. | §18.1.4 p. 642, Fig. 18.6, 18.7 |
| Actor to use case | Solid line, normally without heads. | Arrow from actor to use case. | §18.1.4, §11.5.4 |
| «include» | Dashed, open head, **from the base use case to the included one**. | Arrow reversed. | §18.1.4 p. 642, Fig. 18.4 |
| «extend» | Dashed, open head, **from the extending use case to the extended one**, condition in a note. | Arrow pointing like «include». | §18.1.4 p. 642, Fig. 18.3 (head as in the text) |
| Generalization | Solid line, hollow triangle at the general actor or use case. | Open head. | §9.2.4.2 |

### Component diagram

| Element | Drawn as | Typical mistake | Spec (§, Fig.) |
| --- | --- | --- | --- |
| Component | Classifier rectangle with the keyword `«component»` above the bold name. Optionally the component icon in the right hand corner: a rectangle with two smaller rectangles protruding from its left side. With the icon, the keyword may be left out. | Neither keyword nor icon (that is a class). | §11.6.4 p. 210, Fig. 11.39 |
| Provided interface | Circle (ball, lollipop) labelled with the interface name, attached by a **solid** line to the component or to one of its ports. | Dashed line; an arrowhead on the line. | §10.4.4 p. 172, §11.6.4, Fig. 10.8, 11.40 |
| Required interface | Half circle (socket) labelled with the interface name, attached by a **solid** line. The text says only "half-circle"; in every figure it is open on the side **away from** the component that requires the interface. | Socket open toward its own component; ball and socket swapped. | §10.4.4 p. 172, Fig. 10.10, 11.40 |
| Interface as a rectangle | `«interface»` classifier rectangle, to show operations. The component realizes it with a dashed line and a hollow triangle, or uses it with a dashed line, an open head, and `«use»`. | Solid lines; one head style for both. | §11.6.4 p. 210, §10.4.4, Fig. 10.11, 11.43 |
| Dependency between components | Dashed line, open head. | Solid line. | §11.6.5 p. 211, Fig. 11.39 |
| Wiring between components | Dependency (dashed line, open head) from the socket of one component to the ball of the other. | Ball pushed into the socket between two component definitions: that is the notation of an assembly connector between ports of parts, see below. | §11.6.3 p. 210, §10.4.4 p. 172, Fig. 11.46 |
| Port | Small square overlapping the boundary of the classifier or part (or inside it), the name near it: `name : Type`, `~Type` for a conjugated port. Ball and socket of the port are attached to the square. | A circle; a square away from the boundary. | §11.3.4 p. 191, Fig. 11.11 |
| Internal structure | Compartment named "internal structure" below the name compartment. A part is a box with a solid outline and `name : Type` or `:Type`; a role that is not owned by composition has a dashed outline. A part typed by a component has `«component»` above its name. | Parts named without the colon: they then read as definitions, not as parts. | §11.2.4 p. 185-186, Fig. 11.2, 11.47 |
| Connector | **Solid** line between parts or ports, "similar notation to that for Association"; name and multiplicities as on an association. | Dashed line. | §11.2.4 p. 186, Fig. 11.4, 11.5 |
| Assembly connector, ball-and-socket | Optional: the ball of the providing port sits in the socket of the requiring port, each attached by a solid line. Only between **simple ports** (one provided or required interface). | Used for parts without ports or for ports with several interfaces. | §11.2.4 p. 186, Fig. 11.4, 11.8, 11.47 |
| Delegation connector | **Solid** line from a port on the boundary to a part, to a port of a part, or to its ball or socket. No arrowhead, no keyword. | Arrow with an open head and `«delegate»` (see below). | §11.2.4 p. 186, §11.3.3 p. 191, Fig. 11.47, 11.48 |
| Component realization | Dashed line, hollow triangle at the component, from each realizing classifier. | Open head. | §11.6.4 p. 211, Fig. 11.44 |
| Optional compartments | "provided interfaces", "required interfaces", "realizations", "artifacts", "packaged elements": the name centred at the top of the compartment, entries as a list or as nested symbols. | | §11.6.4 p. 210-211, Fig. 11.41, 11.42, 11.45 |

**Delegation has no arrow in UML 2.5.1.** The text asks for "normal Connector notation for
assembly or delegation" (§11.2.4), Fig. 11.47 and 11.48 draw plain lines, and `«delegate»`
is neither in the keyword table (Annex C, Table C.1) nor anywhere else in the document.
Whether a connector delegates follows from where it ends: on a port that is not on a part
(§11.8.10.4). The arrow with `«delegate»` is common in tools and textbooks; if a diagram
uses it, it uses a stereotype of its own, which §11.2.4 allows above a connector name.

Figures that disagree with the text: Fig. 11.43 prints the component icon on the two
`«interface»` rectangles, and Fig. 11.11 draws `«use»` on a solid line without a head; a
usage is a dependency, so dashed with an open head (§7.7.4, Fig. 10.11). Fig. 11.46 marks
an inherited interface with a slash (`/OrderableItem`), which §10.4.4 permits but
discourages in favour of the caret (`^OrderableItem`, Fig. 10.9).

### Deployment diagram

| Element | Drawn as | Typical mistake | Spec (§, Fig.) |
| --- | --- | --- | --- |
| Node | "Perspective view of a cube" with the name inside. An instance is `:AppServer`, underlined. | Flat rectangle. | §19.2.4 p. 654, §19.4.4 p. 658, Fig. 19.3, 19.14 |
| Device | Node with the keyword `«device»`. | | §19.4.4 p. 658, Fig. 19.12 |
| Execution environment | Node with the keyword `«executionEnvironment»` (one word), usually nested in a device. | `«execution environment»`. | §19.4.4 p. 658, Table C.1 p. 747, Fig. 19.12, 19.13 |
| Nested nodes | Node cube drawn inside a node cube. The internal structure of a node consists of nodes only. | | §19.4.3 p. 658, Fig. 19.12 |
| Artifact | Class rectangle with the keyword `«artifact»`, or an icon such as the document icon; the figures show the icon in the top right corner, with the keyword or alone. The name of an instance is underlined; the underline may be omitted. | Folded corner on the whole box (that is a comment). | §19.3.4 p. 657, Fig. 19.9, 19.15 |
| Deployment by nesting | Artifact drawn inside the node, or listed there by name. No label is needed. | | §19.2.4 p. 654, §19.4.4 p. 659, Fig. 19.2, 19.4 |
| Deployment as an arrow | **Dashed** line, **open** head, `«deploy»`, from the artifact to the node. | Head at the artifact; solid line. | §19.2.4 p. 654, §19.4.4 p. 659, Fig. 19.3, 19.15 |
| Communication path | **Solid** line between nodes, as an association; multiplicities at the ends as needed. | Dashed line; arrowheads to show a data flow. | §19.4.4 p. 659, Fig. 19.12, 19.15 |
| Manifestation | **Dashed** line, **open** head, `«manifest»`, from the artifact to the element it embodies, e.g. a component. | Head at the artifact. | §19.3.4 p. 657, Fig. 19.10 |
| Dependency between artifacts | Dashed line, open head, also inside a node. | | §19.2.5, Fig. 19.2 |
| Deployment specification | Classifier rectangle with the keyword `«deployment spec»`, attached with a dependency arrow. | | §19.2.4 p. 654, Fig. 19.5, 19.6 |

§19.2.4 puts a colon before the name of every deployment target; Fig. 19.15 shows nodes at
type level as `AppServer` and `DBServer`, bold, without colon and underline. Use the colon
and the underline for instances, the bold name for types, as for classes and objects.
The figures of clause 19 print instance names bold and underlined; §9.8.4 and §19.3.4 ask
for the underline only.

### Applies to every diagram

- **Guillemets** `«` `»` mark keywords and stereotypes, not `<<` `>>` (Annex C, p. 745).
  If a document uses `«…»` for stereotypes, do not use it for placeholders too; write
  placeholders as *&lt;italic&gt;* instead.
- **Fill colours have no meaning in UML.** If a deck gives a colour a meaning, keep it
  the same on every slide and say so in a legend.

## LaTeX: TikZ styles

[`assets/uml-tikz.sty`](assets/uml-tikz.sty) defines every element above as a TikZ
style (`uml association`, `uml navigable`, `uml navigable both`, `uml navigable one way`,
`uml dependency`, `uml generalization`, `uml realization`, `uml aggregation`,
`uml composition`, `uml flow`, `uml sync`, `uml async`, `uml reply`, `uml create`,
`uml include`, `uml extend`, `uml connector`, `uml delegation`, `uml deploy`,
`uml manifest`, `uml communication path`; nodes `uml class`, `uml class2`, `uml box`,
`uml usecase`, `uml action`, `uml state`, `uml initial`, `uml final`, `uml flow final`,
`uml decision`, `uml bar`, `uml component`, `uml component icon`, `uml port`, `uml ball`,
`uml node`, `uml artifact`, `uml artifact icon`, pic `uml actor`) plus macros
`\umlinstance`, `\umlname`, `\umlkw`, `\umllifeline`, `\umlactivation`, `\umlfragment`,
`\umlnote`, `\umlrake`, `\umlsocket`, `\umlcontainer`.
Open heads are `Straight Barb[length=1.9mm, width=1.7mm]`, filled heads
`Triangle[length=1.9mm, width=1.7mm]`: the same size.
[`assets/uml-tikz-example.tex`](assets/uml-tikz-example.tex) uses each of them once.

```latex
\usepackage{uml-tikz}
...
\begin{tikzpicture}[uml]
  \node[uml class] (a) at (0,0) {\textbf{Appointment}\nodepart{two}\ttfamily - start: LocalDateTime
                                 \nodepart{three}\ttfamily + cancel()};
  \node[uml box] (p) at (45,0) {\textbf{Patient}};
  \draw[uml navigable] (a) -- (p) node[pos=0.8, above, uml label] {0..1};
\end{tikzpicture}
```

Draw aggregation and composition **from the whole to the part**: the diamond is the start
tip. The picture option `uml` sets 1 unit = 1 mm.

Component and deployment diagrams:

```latex
\node[uml component] (svc) at (0,0) {\umlname[component]{BookingService}};
\node[uml ball, label={[uml label]above:Booking}] (b) at (-30,0) {};   % provided interface
\draw (svc.west) -- (b);
\umlsocket{n}{30,0}{0}                    % required interface, open to the right (0 degrees)
\draw (svc.east) -- (n back);
\node[uml port] (p) at (svc.south) {};    % port on the boundary

\umlcontainer[uml node]{srv}{0,-20}{60,-55}{\umlkw{device}\\\umlinstance{}{AppServer}}
\node[uml artifact] (jar) at (30,-42) {\umlname[artifact]{booking.jar}};  % deployed by nesting
```

`\umlsocket{id}{centre}{angle}` draws the half circle open in the direction of the angle
and defines `(id)` at its centre and `(id back)` for the line from the component; a
`uml ball` at the same centre gives the ball-and-socket of an assembly connector.
`\umlcontainer[style]{id}{corner}{corner}{name}` draws a component with room for its
internal structure or a node with nested nodes and artifacts; draw it before its contents.

Build the example with Docker (see the `compile-tex` skill for details), from the folder
that holds both files:

```sh
docker run --rm -v "$PWD:/work" -w /work texlive/texlive:latest latexmk -lualatex uml-tikz-example.tex
```

```powershell
docker run --rm -v "${PWD}:/work" -w /work texlive/texlive:latest latexmk -lualatex uml-tikz-example.tex
```

## PowerPoint: python-pptx library

[`scripts/uml_pptx.py`](scripts/uml_pptx.py) needs Python 3.9+ and `python-pptx`.
Coordinates are points from the top left corner of the slide. `demo` writes a seven-slide
example deck (all relationships; class and object diagram; sequence; activity and state
machine; use case and communication diagram; component diagram; deployment diagram),
`check` lints any deck.

```sh
pip install python-pptx
python scripts/uml_pptx.py demo uml-demo.pptx
python scripts/uml_pptx.py check deck.pptx        # JSON on stdout
```

```powershell
pip install python-pptx
python scripts\uml_pptx.py demo uml-demo.pptx
python scripts\uml_pptx.py check deck.pptx        # JSON on stdout
```

Drawing into a deck, with `scripts/` on `sys.path`:

```python
import uml_pptx as uml

prs = uml.new_presentation()                 # or pptx.Presentation("existing.pptx")
s = uml.blank_slide(prs)                     # or any existing slide

practice = uml.class_(s, 40, 70, 250, "Practice", ["- name: String"], ["+ book(p: Patient): Appointment"])
appt = uml.class_(s, 340, 70, 200, "Appointment", ["- start: LocalDateTime"], ["+ cancel()"])
patient = uml.class_(s, 650, 80, 110, "Patient")
person = uml.class_(s, 650, 180, 110, "Person", abstract=True)

uml.composition(s, practice, appt, whole_mult="1", part_mult="*")
uml.association(s, appt, patient, b_end="navigable", a_mult="*", b_mult="0..1", b_role="patient")
uml.generalization(s, patient, person)
prs.save("booking.pptx")
```

| Function | Draws |
| --- | --- |
| `class_`, `interface`, `object_`, `note` | Class with compartments (bold name, italic if `abstract`, `keyword=` in guillemets); object with underlined `name : Type` and slots; comment. |
| `association(a, b, a_end, b_end)`, `link` | Solid line; each end `None` (unspecified), `"navigable"` (open head) or `"x"`. Multiplicities above, role names below the line. |
| `dependency(client, supplier, keyword)`, `include`, `extend` | Dashed line, open head, `«keyword»` in the middle. |
| `generalization(specific, general)`, `realization(implementing, interface)` | Solid or dashed line ending in a hollow triangle (freeform shape). |
| `aggregation(whole, part)`, `composition(whole, part)` | Hollow or filled diamond at the whole (freeform shape); `part_navigable=True` adds an open head. |
| `actor`, `actor_box`, `subject`, `use_case` | Use case diagram. |
| `action(call=True)`, `initial`, `activity_final`, `flow_final`, `decision`, `bar`, `flow(a, b, guard=)` | Activity diagram. |
| `state(internal=[...])`, `final_state`, `transition(a, b, guard="trigger [guard] / effect")` | State machine. |
| `lifeline`, `actor_lifeline`, `activation`, `message(x1, x2, y, name, kind)`, `self_message`, `fragment` | Sequence diagram; `kind` is `sync`, `async`, `reply`, or `create`. |
| `comm_lifeline`, `communication_message` | Communication diagram. |
| `component(icon=, keyword=, compartment=)`, `port(owner, side)`, `provided_interface(owner, side, name)`, `required_interface(owner, side, name)` | Component with keyword and icon; port square on the boundary; ball and socket on a component or a port. `compartment="internal structure"` leaves room for parts. |
| `assembly(requiring, providing)`, `connector`, `delegation(outer_port, inner)` | Ball-and-socket between two simple ports; plain connector; delegation as a solid line without head. Wiring between component definitions: `dependency(socket, ball)`. |
| `node`, `device`, `execution_environment`, `artifact(icon=, keyword=, instance=)` | Deployment diagram: cube, with keyword; artifact with keyword and document icon. Draw a node before its contents. |
| `deploy(artifact, node)`, `manifest(artifact, element)`, `communication_path(a, b)` | Dashed line with open head and `«deploy»` or `«manifest»`; solid line between nodes. |
| `edge(a, b, via, dash, start, end)`, `label`, `group` | Anything else: polylines through `via` points, free text, PowerPoint group. |

Every edge takes nodes or `(x, y)` points and ends on the outline of a node (rectangle,
ellipse, or diamond). House style: set `uml.INK`, `uml.PAPER`, `uml.NODE_WIDTH`,
`uml.EDGE_WIDTH`, `uml.HEAD_W`, `uml.HEAD_LEN`, `uml.TRIANGLE`, `uml.DIAMOND`,
`uml.FONT`, `uml.MONO`, `uml.FONT_SIZE` before drawing.

`check` reports sizes below zero, line ends without a UML meaning, open and filled heads
of different size on one slide, and keywords written as `<<keyword>>`.

## What python-pptx and PowerPoint get wrong on their own

- **Arrowheads have no python-pptx API.** Add `<a:tailEnd>` (end of the line) or
  `<a:headEnd>` (start) to the `a:ln` of the connector. `type="arrow"` is the **open**
  head (two strokes), `type="triangle"` the **filled** head. `stealth`, `diamond`, and
  `oval` have no UML meaning; `check` reports them.
- **There is no hollow triangle and no hollow diamond line end.** PowerPoint's
  `type="diamond"` is a small filled rhombus at the line's own scale. Draw the hollow
  triangle and both diamonds as closed freeform shapes with a white or black fill, and let
  the line stop at the triangle's base or the diamond's far corner; the library does this.
- **Give open and filled heads the same `w` and `len`.** Their size scales with the line
  width: on a 1 pt line, `med` is barely visible, `lg` reads well. `check` reports a slide
  whose open and filled heads differ in size.
- **Schema order inside `a:ln`:** fill, `prstDash`, join, `headEnd`, `tailEnd`. A head
  inserted before the fill, or `tailEnd` before `headEnd`, breaks the file.
- **Connectors take a shadow from the theme.** Shapes drawn with python-pptx reference
  the theme style (`p:style`); remove it and set fill and line explicitly.
- **Rounded corners.** `ROUNDED_RECTANGLE` with the default adjustment is too round for
  an action or state; set `adjustments[0]` to radius / shorter side.
- **Underline and bold are run properties.** An object name needs
  `run.font.underline = True` and `bold = False`; a class name the opposite.
- **Negative width or height.** python-pptx writes and reloads such a file, PowerPoint
  refuses to open it. `check` reports it.
- **Freeform vertices are integers.** `build_freeform` rounds every point to its unit; an
  arc of a few points across (the socket) gets corners. Pass a finer `scale`, as the
  library does (1/100 pt).
- **The cube preset shades its faces.** `MSO_SHAPE.CUBE` darkens the top and the side
  face of the fill; the library draws the node from a rectangle and a polygon instead.

## Other LaTeX packages for UML

[How to draw UML diagrams](https://github.com/latextemplates/gadr-latex-packages/blob/main/uml-diagrams.md)
in `latextemplates/gadr-latex-packages` compares the ready-made routes: PlantUML (`plantuml`
package), `MetaUML`, `pgf-umlcd` and `pgf-umlsd`, `pst-uml`, tikz-uml, and Mermaid
(`ltMermaid`). For each it has the same small examples (a sequence diagram, class
relations, class visibility, components) with source and rendering in
[`uml-diagrams/`](https://github.com/latextemplates/gadr-latex-packages/tree/main/uml-diagrams),
what each needs to compile (engine, `--shell-escape`, external tools, the TeX Live Docker
image), the lines of code per example, and pros and cons.

- **Use that comparison** when the question is which package to take: the diagram should
  be laid out automatically from a short text (PlantUML, Mermaid), the package has to be
  in TeX Live or work without `--shell-escape`, or a document already uses one of them.
- **Use `uml-tikz.sty`** when the notation has to be right element by element, when the
  diagram type is outside those examples (activity, state machine, use case,
  communication, deployment, internal structure with ports), when the diagram is part of
  a larger TikZ picture, or when it should match a PowerPoint version drawn with
  `uml_pptx.py`. It is a set of styles, not a layout engine: every position is given.
- **Use both** by drawing with a package and checking the result against the checklists
  above. The comparison rates effort and tooling, not conformance with UML 2.5.1, and the
  packages have defaults of their own: in its renderings `pgf-umlsd` underlines lifeline
  heads and draws `\mess` with an open head (asynchronous) where the other packages draw
  the same call with a filled one, tikz-uml heads a lifeline `Alice:`, and all three
  component examples put a ball into a socket between components without ports.

## Verify: render, enlarge, compare

A diagram is done when a rendering of it has been compared with the cited spec figures,
element by element, in enlarged crops: head filled or open, two strokes or a triangle,
number of heads, which end, solid or dashed, diamond at the whole, rounded or square
corners, underline and bold. When delegating the check, hand over the rendered image and
the spec figures and ask for exactly this comparison.

On Windows with PowerPoint, [`scripts/render.ps1`](scripts/render.ps1) writes one PNG per
slide (a running PowerPoint is reused and left open):

```powershell
pwsh scripts\render.ps1 deck.pptx out-png 2880
```

Elsewhere, LibreOffice converts to PDF; its rendering of line ends can differ from
PowerPoint's, and this library was checked with PowerPoint only:

```sh
soffice --headless --convert-to pdf deck.pptx
```

The spec figures can be cut out of the spec PDF with PyMuPDF
(`page.get_pixmap(dpi=200, clip=rect)`) for side-by-side crops.

## Sources

- OMG: *Unified Modeling Language (UML)*, version 2.5.1, formal/17-12-05, 2017.
  <https://www.omg.org/spec/UML/2.5.1/> (PDF: <https://www.omg.org/spec/UML/2.5.1/PDF>).
- latextemplates: *How to draw UML diagrams*, a comparison of LaTeX packages for UML.
  <https://github.com/latextemplates/gadr-latex-packages/blob/main/uml-diagrams.md>
- Related skill: [`fmc`](../fmc/SKILL.md) for FMC block diagrams, whose arrowheads are
  all filled.

The specification is not bundled; this skill cites it by clause and figure and quotes
only single sentences where they decide a case. The styles, the library, and the
examples are drawn from scratch and are MIT-licensed like the rest of this repository.
