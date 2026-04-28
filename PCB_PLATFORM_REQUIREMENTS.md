# Production-Grade Requirements for AI PCB Design Automation Platform

## Document Control
- **Version**: 1.0
- **Date**: 2026-04-28
- **Status**: Draft for Review
- **Author**: Research Compilation

---

## 1. DRC (Design Rule Check) Standards

### 1.1 IPC Standards for PCB Design

The **IPC (Association Connecting Electronics Industries)** is the primary standards body for PCB design and manufacturing. Their standards are ANSI-accredited and globally adopted.

#### Core Design Standards

| Standard | Title | Purpose |
|----------|-------|---------|
| **IPC-2221** | Generic Standard on Printed Board Design | Base design requirements for all PCB types |
| **IPC-2222** | Sectional Design Standard for Rigid Organic PCBs | Specific to rigid boards |
| **IPC-2223** | Sectional Design Standard for Flexible Printed Boards | Flex and rigid-flex designs |
| **IPC-2141A** | Design Guide for High-Speed Controlled Impedance Circuit Boards | Signal integrity design |
| **IPC-2251** | Design Guide for Packaging of High-Speed Electronic Circuits | High-speed packaging |
| **IPC-7351B** | Generic Requirements for Surface Mount Design and Land Pattern Standards | SMT footprint design |

#### Performance & Acceptance Standards

| Standard | Title | Purpose |
|----------|-------|---------|
| **IPC-A-600** | Acceptability of Printed Boards | Visual quality acceptance criteria |
| **IPC-A-610** | Acceptability of Electronic Assemblies | Assembly workmanship standards |
| **IPC-6011** | Generic Performance Specification for Printed Boards | Base performance specs |
| **IPC-6012** | Qualification and Performance Spec for Rigid Printed Boards | Rigid board performance |
| **IPC-6013** | Specification for Flexible/Rigid-Flex Printed Wiring | Flex board performance |

#### IPC Product Classes

- **Class 1**: General Electronic Products (consumer, toys, non-critical)
- **Class 2**: Dedicated Service Electronic Products (communications, business, instruments)
- **Class 3**: High Performance/Harsh Environment (medical, aerospace, military, life-critical)

> **Platform Requirement**: The AI PCB platform MUST support all three IPC classes and allow the user to select the target class at project initiation. Default should be **Class 2**.

### 1.2 Mandatory DRC Rules for Production

The following DRC categories are **mandatory** for any production-grade PCB design tool:

#### 1.2.1 Electrical Rules

| Rule Category | Parameters | Criticality |
|---------------|------------|-------------|
| **Clearance (Spacing)** | Trace-to-trace, trace-to-pad, pad-to-pad, trace-to-via, via-to-via, copper-to-board-edge | CRITICAL |
| **Trace Width** | Minimum width per layer, current-carrying capacity (IPC-2152) | CRITICAL |
| **Short Circuit** | No unintended electrical connections | CRITICAL |
| **Unconnected Net** | All nets must be fully routed (or intentionally unconnected with flag) | CRITICAL |
| **Net Length** | Maximum/minimum net length constraints | HIGH |
| **Loop Detection** | Unintended ground loops | HIGH |

#### 1.2.2 Manufacturing Rules

| Rule Category | Parameters | Criticality |
|---------------|------------|-------------|
| **Annular Ring** | Minimum copper ring around drilled holes (IPC-2221: Class 2 = 0.05mm min, Class 3 = 0.075mm min) | CRITICAL |
| **Drill Hole Size** | Minimum hole diameter, aspect ratio limits | CRITICAL |
| **Hole-to-Hole Spacing** | Edge-to-edge distance between drilled holes | CRITICAL |
| **Board Edge Clearance** | Copper keepout from board edge (typically 0.3-0.5mm) | CRITICAL |
| **Solder Mask Dam** | Minimum web width between exposed pads | HIGH |
| **Silkscreen Clearance** | Minimum clearance to pads, vias, and exposed copper | MEDIUM |
| **Fiducial Requirements** | Global and local fiducial placement for assembly | MEDIUM |

#### 1.2.3 Component Rules

| Rule Category | Parameters | Criticality |
|---------------|------------|-------------|
| **Footprint Validation** | Pad count matches symbol pin count | CRITICAL |
| **Courtyard Overlap** | Component keepout areas must not overlap | HIGH |
| **Component Height** | Maximum component height per board region | MEDIUM |
| **Component Orientation** | Polarized components correctly oriented | HIGH |
| **SMD-to-Lead Spacing** | Clearance between SMD pads and through-hole leads | HIGH |

#### 1.2.4 High-Speed Rules

| Rule Category | Parameters | Criticality |
|---------------|------------|-------------|
| **Length Matching** | Tolerance for matched-length groups (e.g., DDR, USB) | HIGH |
| **Differential Pair Spacing** | Intra-pair and inter-pair spacing | HIGH |
| **Impedance Control** | Target impedance with tolerance (typically ±10%) | HIGH |
| **Via Stub Length** | Maximum via stub for high-speed signals | MEDIUM |
| **Return Path Continuity** | Uninterrupted reference plane under signals | HIGH |

### 1.3 Common DRC Rule Sets

The platform MUST ship with the following pre-configured rule sets:

#### Standard Manufacturer Rule Sets
- **JLCPCB Standard**: 5/5mil trace/space, 0.3mm drill, 4 layers max (default)
- **JLCPCB Advanced**: 3.5/3.5mil, 0.2mm drill, 6-8 layers, impedance control
- **PCBWay Standard**: 5/5mil, 0.3mm drill, standard stackup
- **PCBWay Advanced**: 3/3mil, 0.15mm drill, HDI capabilities
- **OSH Park**: 6/6mil, 2-layer purple, 4-layer options
- **Eurocircuits Standard**: 5/5mil, IEC quality standards
- **Seeed Studio**: 6/6mil standard, 4/4mil advanced

#### IPC-Based Rule Sets
- **IPC-2221 Class 1**: Consumer grade, relaxed tolerances
- **IPC-2221 Class 2**: Industrial grade, standard tolerances (default)
- **IPC-2221 Class 3**: Mission-critical, tight tolerances
- **IPC-6012 Class 3/A**: Aerospace-grade with annular ring requirements

#### Application-Specific Rule Sets
- **High-Speed Digital**: Optimized for DDR4/5, PCIe, USB3.x
- **RF/Microwave**: Controlled dielectric, minimal via stubs
- **Power Electronics**: Heavy copper, wide clearances, thermal management
- **Wearable/Flex**: Flex bend radius, coverlay requirements

> **Platform Requirement**: Users MUST be able to create custom rule sets by extending existing templates. Rule sets MUST be version-controlled and exportable/importable as JSON/XML.

---

## 2. DFM (Design for Manufacturing) Checks

### 2.1 What Manufacturers Check Before Fabrication

DFM analysis occurs at two levels: **Fabrication DFM** (bare board) and **Assembly DFM** (populated board).

#### 2.1.1 Fabrication DFM Checks

| Check | Description | Failure Mode |
|-------|-------------|--------------|
| **Minimum Trace Width/Spacing** | Can the fabricator reliably etch this geometry? | Open circuits, shorts |
| **Aspect Ratio** | Hole depth-to-diameter ratio (typically max 10:1 for standard, 15:1 advanced) | Plating voids, broken barrels |
| **Copper Balance** | Even copper distribution across board | Board warp, lamination issues |
| **Thermal Relief** | Proper thermal relief for plane connections | Soldering difficulties |
| **Soldermask Web** | Minimum width of solder mask between pads | Mask peeling, solder bridging |
| **Silkscreen Legibility** | Text height and width vs. manufacturer capabilities | Unreadable labels |
| **Edge Clearance** | Copper and components from routing edge | Damage during depanelization |
| **Slot/Route Tolerances** | Non-plated slots and internal cutouts | Dimensional issues |
| **Layer Registration** | Alignment between layers | Misregistration causing shorts/opens |
| **Sliver Detection** | Narrow copper slivers that may detach | Shorts, contamination |

#### 2.1.2 Assembly DFM Checks

| Check | Description | Failure Mode |
|-------|-------------|--------------|
| **Component Spacing** | Minimum spacing for pick-and-place machines | Assembly collisions, rework |
| **Pad-to-Part Body** | Solder mask vs. component body overlap | Tombstoning, poor soldering |
| **Heatsink Accessibility** | Thermal pad access for soldering | Insufficient thermal contact |
| **Test Point Accessibility** | Probe access for ICT/flying probe | Untestable circuits |
| **Component Orientation** | Consistent orientation for polarized parts | Wrong component placement |
| **Reflow Thermal Profile** | Component temperature sensitivity compatibility | Component damage |
| **Wave Solder Considerations** | Through-hole component orientation to wave | Solder skips, bridges |
| **BGA Breakout** | Escape routing feasibility for fine-pitch BGAs | Unmanufacturable high-density designs |

### 2.2 Major Manufacturer Design Rules

#### JLCPCB Design Rules (Standard vs. Advanced)

| Parameter | Standard | Advanced |
|-----------|----------|----------|
| Min Trace Width | 5 mil (0.127mm) | 3.5 mil (0.09mm) |
| Min Trace Spacing | 5 mil (0.127mm) | 3.5 mil (0.09mm) |
| Min Via Drill | 0.3mm | 0.2mm |
| Min Via Pad | 0.6mm | 0.4mm |
| Min Hole-to-Hole | 0.5mm | 0.25mm |
| Max Board Size | 500mm x 500mm | 500mm x 500mm |
| Max Layers | 4 | 8 |
| Controlled Impedance | Yes (4-layer+) | Yes |
| Blind/Buried Vias | No | Yes (6-layer+) |

#### PCBWay Design Rules

| Parameter | Standard | Advanced |
|-----------|----------|----------|
| Min Trace Width | 5 mil | 3 mil |
| Min Trace Spacing | 5 mil | 3 mil |
| Min Via Drill | 0.2mm | 0.15mm |
| Min Annular Ring | 0.15mm | 0.075mm |
| Max Aspect Ratio | 8:1 | 12:1 |
| Controlled Impedance | ±10% | ±10% |

#### OSH Park Design Rules

| Parameter | 2-Layer | 4-Layer |
|-----------|---------|---------|
| Min Trace Width | 6 mil | 5 mil |
| Min Trace Spacing | 6 mil | 5 mil |
| Min Via Drill | 0.25mm | 0.25mm |
| Min Via Pad | 0.5mm | 0.5mm |
| Max Board Size | 16in x 16in | 16in x 16in |
| Unique Feature | Purple solder mask default | ENIG finish included |

### 2.3 Common DFM Failures and Prevention

#### Top 10 DFM Failures

1. **Acute Angle Traces (Acid Traps)**
   - **Problem**: Trace angles < 90 degrees can trap etchant, causing over-etching
   - **Prevention**: Enforce minimum 90 degree angles, preferably 135 degree or rounded corners
   - **Check**: DRC rule for minimum included angle

2. **Copper Slivers**
   - **Problem**: Thin copper islands that can lift during processing and cause shorts
   - **Prevention**: Minimum copper island area rule (e.g., 0.1mm squared)
   - **Check**: Sliver detection algorithm

3. **Starved Thermals**
   - **Problem**: Thermal relief spokes too thin or too few, causing soldering issues
   - **Prevention**: Minimum spoke width (typically 0.2-0.25mm), minimum 2 spokes
   - **Check**: Thermal relief validation

4. **Silkscreen on Pads**
   - **Problem**: Silkscreen ink on solderable surfaces preventing wetting
   - **Prevention**: Automatic clipping of silkscreen to solder mask openings
   - **Check**: Silkscreen-to-pad clearance (typically 0.15mm)

5. **Unmasked Vias Under Components**
   - **Problem**: Solder wicking into vias during reflow, starving joints
   - **Prevention**: Tented vias or via plugging under SMD components
   - **Check**: Via tenting rule for regions under SMD pads

6. **Insufficient Annular Ring**
   - **Problem**: Drill wander breaks plated hole connection
   - **Prevention**: Minimum annular ring per IPC class (Class 2: 0.05mm, Class 3: 0.075mm)
   - **Check**: Annular ring calculator and DRC

7. **Non-Optimal Panelization**
   - **Problem**: Poor array design causing depanelization damage
   - **Prevention**: Standard panel sizes, proper tabs/routing, fiducial placement
   - **Check**: Panelization advisor tool

8. **Missing or Inadequate Fiducials**
   - **Problem**: Assembly machines cannot locate board precisely
   - **Prevention**: 3 global fiducials minimum, local fiducials for fine-pitch components
   - **Check**: Fiducial placement validator

9. **Component-to-Edge Violations**
   - **Problem**: Components too close to board edge damaged during handling
   - **Prevention**: Keepout distance (typically 5mm for handling, 3mm for wave solder)
   - **Check**: Component-to-edge DRC

10. **Unbalanced Copper**
    - **Problem**: Uneven copper distribution causing board warp
    - **Prevention**: Copper pour balance, hatched planes where appropriate
    - **Check**: Copper density analysis (target 40-60% per layer)

> **Platform Requirement**: The AI agent MUST run a comprehensive DFM report before declaring a design complete. The report MUST categorize findings as **Critical** (must fix), **Warning** (should fix), or **Info** (advisory).


---

## 3. Signal Integrity (SI) Basics

### 3.1 High-Speed Rules That Matter

Signal integrity becomes critical when the **rise time** of a signal is less than approximately **3 times the propagation delay** across the trace. For FR-4, propagation delay is roughly **1 ns per 15 cm (6 in)**.

#### When Does SI Become Critical?

| Signal Edge Rate | Critical Trace Length | Approximate Frequency |
|------------------|----------------------|----------------------|
| 1 ns | > 5 cm (2 in) | > 300 MHz |
| 500 ps | > 2.5 cm (1 in) | > 600 MHz |
| 200 ps | > 1 cm (0.4 in) | > 1.5 GHz |
| 50 ps | > 2.5 mm (0.1 in) | > 6 GHz |

**Rule of Thumb**: If your design contains signals above **100 MHz** or has edge rates faster than **1 ns**, you MUST consider signal integrity.

### 3.2 Key SI Parameters

#### 3.2.1 Impedance Control

| Parameter | Typical Values | Notes |
|-----------|---------------|-------|
| **Single-Ended** | 50 Ohm ± 10% | Standard for most digital signals |
| **Differential (USB 2.0)** | 90 Ohm ± 10% | Twisted-pair equivalent |
| **Differential (USB 3.x/PCIe)** | 85-100 Ohm ± 10% | Protocol-dependent |
| **Differential (Ethernet)** | 100 Ohm ± 10% | CAT5/6 cable matching |
| **DDR4/DDR5 Data** | 40 Ohm single-ended, 80 Ohm differential | On-die termination |

**Impedance depends on**:
- Trace width
- Trace-to-reference-plane distance (dielectric thickness)
- Dielectric constant (Dk) of substrate (FR-4: ~4.3-4.5)
- Adjacent trace spacing (for differential pairs)

#### 3.2.2 Length Matching

| Interface | Match Group | Tolerance | Notes |
|-----------|------------|-----------|-------|
| **DDR3 Address/Command** | All A/C signals | ±25 mils (0.635mm) | To clock |
| **DDR3 Data** | DQ + DQS | ±10 mils (0.254mm) | Within byte lane |
| **DDR4 Address/Command** | All A/C signals | ±20 mils (0.508mm) | To clock |
| **DDR4 Data** | DQ + DQS + DM | ±5 mils (0.127mm) | Per byte lane |
| **USB 2.0 D+/D-** | Pair only | ±10 mils (0.254mm) | Differential |
| **USB 3.x SSTX/RX** | Pair only | ±5 mils (0.127mm) | Differential |
| **PCIe Gen 3/4** | Pair only | ±2 mils (0.05mm) | Very tight |
| **MIPI DSI/CSI** | Lane pairs | ±5 mils (0.127mm) | Differential lanes |

#### 3.2.3 Differential Pair Rules

| Parameter | Requirement |
|-----------|-------------|
| **Intra-pair Spacing** | Typically equal to trace width (1W), or as required for impedance |
| **Length Matching Method** | Serpentine tuning at signal end, not in middle |
| **Phase Matching** | Match positive and negative within 5 mils for most interfaces |
| **Coupling** | Tightly coupled preferred for EMI, loosely coupled for density |
| **Reference Plane** | Same reference plane for both traces (GND preferred) |
| **Via Symmetry** | Both traces should have identical via transitions |

### 3.3 SI Best Practices for AI PCB Generation

#### Routing Guidelines

1. **Reference Plane Integrity**
   - Never route high-speed signals across plane splits
   - Provide continuous return path under entire trace length
   - Use stitching vias near layer transitions

2. **Via Minimization**
   - Minimize vias on high-speed traces (ideally 0-2)
   - Use backdrilling for high-speed signals on thick boards (>2mm)
   - Ensure via stub length < 1/10 of signal wavelength

3. **Crosstalk Mitigation**
   - Maintain 3W spacing (3 times trace width) between single-ended signals
   - Maintain 5W spacing between differential pairs
   - Route traces perpendicular on adjacent layers
   - Increase spacing for long parallel runs (>2.5cm)

4. **Termination Strategy**
   - Series termination at source for point-to-point single-ended
   - Parallel termination at load for multidrop or long traces
   - On-die termination (ODT) for DDR memory interfaces
   - Differential termination at receiver end

5. **Clock Routing**
   - Route clocks first, treat as most critical signals
   - Maintain constant impedance and minimize vias
   - Shield clock traces with ground on both sides when possible
   - Keep clocks away from I/O and power switching regions

> **Platform Requirement**: The AI agent MUST identify high-speed interfaces from the schematic/netlist and automatically apply appropriate SI constraints. It MUST warn users if a design contains signals requiring SI attention but no constraints have been defined.


---

## 4. Agent/Workflow Best Practices

### 4.1 AI Agent Architecture for PCB Generation

The AI agent should follow a **pipeline architecture** with discrete, validated stages. Each stage MUST produce verifiable artifacts before proceeding.

```
User Intent -> Intent Parser -> Requirements Document -> Schematic + ERC ->
Placement + Thermal Check -> Routing + DRC -> DFM Analysis ->
Fabrication Output -> Final Validation -> Deliverables
```

### 4.2 Step-by-Step Workflow

#### Stage 1: Intent to Requirements (Input Validation)

**Input**: Natural language description, block diagram, or specification document
**Output**: Structured requirements document (JSON/YAML)

**Validation Gates**:
- [ ] Intent is unambiguous and within platform capabilities
- [ ] Target IPC class is specified or defaulted to Class 2
- [ ] Manufacturer/design rules are selected
- [ ] Power requirements are quantified (voltage, current, noise)
- [ ] High-speed interfaces are identified and categorized
- [ ] Mechanical constraints are defined (dimensions, mounting, connectors)
- [ ] Environmental requirements are noted (temperature, humidity, vibration)

**Error Handling**:
- If intent is ambiguous, agent MUST ask clarifying questions (max 3 rounds)
- If requirements are contradictory, agent MUST highlight conflicts and suggest resolutions
- If design is beyond platform capabilities, agent MUST reject with explanation

#### Stage 2: Requirements to Schematic (Logical Design)

**Input**: Structured requirements document
**Output**: Schematic file (KiCad/Altium/EAGLE format) + netlist + BOM

**Agent Responsibilities**:
1. Select components from validated library (in-stock, not obsolete)
2. Create hierarchical schematic blocks for complex designs
3. Assign reference designators consistently
4. Annotate all nets with meaningful names
5. Add test points and debug interfaces as specified
6. Include decoupling capacitors per IC requirements (typically 0.1uF per power pin, bulk capacitors per rail)
7. Add power and ground symbols clearly

**Validation Gates**:
- [ ] **ERC (Electrical Rule Check)** passes with 0 errors
  - No unconnected pins (unless intentionally NC)
  - No conflicting power outputs
  - No floating inputs on CMOS devices
  - Net labels match physical connections
- [ ] BOM is complete with manufacturer part numbers (MPNs)
- [ ] All components have valid footprints assigned
- [ ] Power budgets are calculated and documented
- [ ] Thermal calculations for power devices are complete

**Error Handling**:
- ERC errors MUST be fixed before proceeding
- Missing footprints MUST be flagged for user creation or auto-generated from IPC-7351
- Components without stock MUST be flagged with alternatives

#### Stage 3: Schematic to Placement (Physical Layout)

**Input**: Schematic + netlist + BOM
**Output**: Component placement file (.pos) + initial board outline

**Agent Responsibilities**:
1. Define board outline based on mechanical constraints
2. Place connectors at board edges per mechanical requirements
3. Group related components into functional blocks
4. Place decoupling capacitors adjacent to power pins (minimize loop area)
5. Orient components for optimal routing and assembly
6. Ensure thermal considerations (heatsinks, airflow)
7. Place fiducials and mounting holes

**Placement Strategy**:
1. Fixed components first (connectors, switches, LEDs, mounting holes)
2. Critical/high-speed ICs second (processors, memory, PHYs)
3. Power circuitry third (regulators, inductors, bulk caps)
4. Remaining passive components last

**Validation Gates**:
- [ ] All components placed (0 unplaced)
- [ ] Courtyard clearances satisfied
- [ ] Component height constraints respected
- [ ] Thermal analysis passes (junction temps within spec)
- [ ] Assembly accessibility verified (pick-and-place clearances)
- [ ] Test point accessibility verified

**Error Handling**:
- If components do not fit in specified outline, agent MUST suggest outline changes or higher density
- If thermal limits exceeded, agent MUST suggest heatsinks, larger copper pours, or component changes
- If assembly clearances violated, agent MUST reposition components

#### Stage 4: Placement to Routing (Interconnect)

**Input**: Placement + netlist + design rules
**Output**: Fully routed PCB with copper pours

**Agent Routing Strategy**:
1. **Power/Ground Planes**: Define layer stackup, assign solid ground plane(s), route power rails
2. **Critical Signals First**: Clocks, high-speed differentials, RF traces
3. **Memory Interfaces**: Route by byte lane, match lengths within tolerance
4. **Remaining Digital**: Route bus structures, general signals
5. **Cleanup**: Optimize trace paths, add teardrops, verify copper pours

**Validation Gates**:
- [ ] **DRC** passes with 0 errors
- [ ] **SI constraints** satisfied (length matching, differential spacing, impedance)
- [ ] **Power integrity**: IR drop analysis passes for high-current rails
- [ ] **Thermal**: High-current traces sized correctly (IPC-2152)
- [ ] **Manufacturing**: All traces respect fabricator rules

**Error Handling**:
- If DRC violations cannot be resolved by rerouting, agent MUST suggest:
  - Additional layers
  - Smaller components
  - Design rule relaxation (with user approval)
- If length matching cannot be achieved, agent MUST report which group violates tolerance

#### Stage 5: Routing to DFM Analysis

**Input**: Routed PCB + design rules + manufacturer capabilities
**Output**: DFM report + suggested fixes

**Agent DFM Checks**:
1. Run all fabrication DFM checks (Section 2.1.1)
2. Run all assembly DFM checks (Section 2.1.2)
3. Generate copper balance report
4. Validate panelization feasibility
5. Check test point coverage (target: 80%+ node access)

**Validation Gates**:
- [ ] Zero Critical DFM findings
- [ ] All Warning findings documented with risk assessment
- [ ] Test point coverage meets target
- [ ] Fabrication cost estimate generated

**Error Handling**:
- Critical findings MUST be fixed before proceeding
- Warnings SHOULD be fixed or explicitly accepted by user
- If design cannot meet DFM requirements, agent MUST suggest alternative manufacturers or design changes

#### Stage 6: DFM to Output (Fabrication Data)

**Input**: Clean PCB + manufacturing specifications
**Output**: Gerber RS-274X + drill files + pick-and-place + BOM + drawings

**Agent Output Generation**:
1. Generate Gerber files per layer (top/bottom copper, mask, silk, paste, inner layers)
2. Generate NC drill files (plated and non-plated, separate if required)
3. Generate pick-and-place file (centroid/XY data)
4. Generate assembly drawings (PDF)
5. Generate fabrication drawing with stackup and notes
6. Generate netlist for electrical test comparison
7. Package all files in manufacturer-preferred format (zip with README)

**Validation Gates**:
- [ ] Gerber files pass DFM tool validation (e.g., JLCDFM, PCBWay checker)
- [ ] Drill file matches hole list
- [ ] Netlist matches schematic
- [ ] BOM matches placed components
- [ ] README includes layer stackup, material specs, finish requirements

### 4.3 Error Handling and Recovery Strategies

#### General Error Handling Philosophy

1. **Fail Fast**: Detect errors as early as possible in the pipeline
2. **Graceful Degradation**: If optimal solution is impossible, find acceptable alternative
3. **Transparency**: Every decision MUST be explainable to the user
4. **Human-in-the-Loop**: Critical decisions require user confirmation

#### Recovery Strategies by Stage

| Stage | Common Failure | Recovery Strategy |
|-------|---------------|-------------------|
| **Intent Parsing** | Ambiguous requirements | Ask clarifying questions, provide examples |
| **Schematic** | ERC failures | Auto-fix where safe (add NC flags, connect power); flag for user otherwise |
| **Placement** | Components do not fit | Suggest larger board, smaller packages, or reduced BOM |
| **Routing** | Unroutable design | Add layers, relax rules, or suggest autorouter parameters |
| **DRC** | Annular ring violations | Increase pad sizes or select different manufacturer |
| **DFM** | Copper imbalance | Add dummy copper pours or hatched planes |
| **Output** | Gerber anomalies | Regenerate with different aperture settings |

#### Retry and Backtracking Policy

- Agent MAY retry a stage up to **3 times** with adjusted parameters
- If stage fails after 3 attempts, agent MUST backtrack to previous stage with revised strategy
- User MUST be notified of all backtracking events with explanation
- Agent MUST preserve all successfully completed stage outputs for rollback

### 4.4 Validation Checkpoints

Before declaring any stage complete, the agent MUST:

1. **Run Automated Checks**: Execute all relevant DRC/ERC/DFM tools
2. **Compare Against Requirements**: Verify outputs match structured requirements document
3. **Log Decisions**: Record all design decisions and their rationale in a design log
4. **Generate Diff**: If revising an existing design, show user what changed
5. **Estimate Confidence**: Report confidence score (0-100%) for each stage completion


---

## 5. API/Backend Production Requirements

### 5.1 What Makes an API Production-Grade for Hardware Design

A production-grade PCB design API must handle:
- **Complex, long-running jobs** (placement and routing can take minutes to hours)
- **Large file uploads/downloads** (Gerber sets, CAD files, 3D models)
- **High precision data** (coordinates in microns, impedance values)
- **Version-sensitive artifacts** (designs must be reproducible)
- **Regulatory compliance** (IP protection, export control for advanced technology)

### 5.2 API Design Principles

#### RESTful Resource Model

| Resource | Endpoints | Description |
|----------|-----------|-------------|
| **Projects** | POST /projects, GET /projects/{id} | Design project container |
| **Requirements** | POST /projects/{id}/requirements | Structured design requirements |
| **Schematics** | POST /projects/{id}/schematics, GET .../netlist | Schematic capture output |
| **Layouts** | POST /projects/{id}/layouts, GET .../placement | Physical layout data |
| **Design Rules** | GET /design-rules, GET /design-rules/{id} | DRC/DFM rule sets |
| **Jobs** | POST /jobs, GET /jobs/{id} | Long-running operation tracking |
| **Outputs** | GET /projects/{id}/outputs/gerbers | Fabrication data export |

#### HTTP Method Semantics

- **GET**: Retrieve resource (idempotent, safe)
- **POST**: Create new resource or submit job (not idempotent)
- **PUT**: Update entire resource (idempotent)
- **PATCH**: Partial update (idempotent)
- **DELETE**: Remove resource (idempotent)

> **Platform Requirement**: All endpoints MUST return consistent error structures with `error_code`, `message`, `details`, and `suggestion` fields.

### 5.3 Rate Limiting

#### Rate Limit Tiers

| Tier | Requests/Min | Requests/Hour | Concurrent Jobs | Use Case |
|------|-------------|---------------|-----------------|----------|
| **Free** | 10 | 100 | 1 | Hobbyists, evaluation |
| **Pro** | 60 | 2,000 | 3 | Small businesses |
| **Enterprise** | 300 | 10,000 | 10 | High-volume design houses |
| **Unlimited** | Custom | Custom | Custom | OEM partners |

#### Rate Limit Headers

Every API response MUST include:
- `X-RateLimit-Limit`: Maximum requests allowed in window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: UTC timestamp when limit resets
- `Retry-After`: Seconds to wait when rate limited (429 response)

#### Rate Limit Response

```json
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1714291200
Retry-After: 45

{
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "API rate limit exceeded. Please slow down your requests.",
  "details": "You have exceeded 60 requests per minute.",
  "suggestion": "Wait 45 seconds before retrying, or upgrade to Pro tier.",
  "retry_after": 45
}
```

### 5.4 Validation

#### Input Validation Layers

1. **Transport Validation**: HTTPS only, max request size (100MB for uploads, 10MB for JSON)
2. **Syntax Validation**: JSON schema validation, file format checks (Gerber, KiCad, etc.)
3. **Semantic Validation**: Business logic checks (design rules consistency, component existence)
4. **Security Validation**: Authentication, authorization, file type whitelisting

#### Validation Error Format

```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "details": [
    {
      "field": "design_rules.min_trace_width",
      "issue": "Value 0.01mm is below manufacturer minimum of 0.09mm",
      "constraint": "min_trace_width >= 0.09mm"
    },
    {
      "field": "components.U1.footprint",
      "issue": "Footprint 'TQFP-48_CUSTOM' not found in library",
      "suggestion": "Use 'TQFP-48_7x7mm_P0.5mm' from standard library"
    }
  ],
  "suggestion": "Review and correct the listed fields before resubmitting."
}
```

### 5.5 Idempotency

#### Idempotency Key Pattern

For mutating operations (POST/PUT/PATCH), clients SHOULD provide an `Idempotency-Key` header:

```
POST /projects/{id}/jobs
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000

{
  "job_type": "auto_route",
  "parameters": { ... }
}
```

**Server Behavior**:
- First request with new key: Process normally, store response for 24 hours
- Duplicate request with same key: Return stored response (201 or 200)
- Duplicate request with different body but same key: Return 409 Conflict

**Idempotency Key Requirements**:
- UUID v4 format strongly recommended
- Keys expire after 24 hours
- Keys are scoped to the authenticated user
- Idempotent responses include `Idempotency-Key` header in response

### 5.6 Async Job Processing

#### Job Lifecycle

```
queued -> validating -> running -> succeeded
                            |
                            -> failed
                            |
                            -> cancelled
```

#### Job Submission Response

```json
HTTP/1.1 202 Accepted
Location: /jobs/123e4567-e89b-12d3-a456-426614174000

{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "queued",
  "estimated_duration_seconds": 300,
  "queue_position": 3,
  "created_at": "2026-04-28T12:00:00Z",
  "links": {
    "self": "/jobs/123e4567-e89b-12d3-a456-426614174000",
    "cancel": "/jobs/123e4567-e89b-12d3-a456-426614174000/cancel",
    "result": "/jobs/123e4567-e89b-12d3-a456-426614174000/result"
  }
}
```

#### Job Polling vs. Webhooks

**Polling** (for simple clients):
```
GET /jobs/{id}
```
- Return current status, progress percentage, and any partial results
- Polling interval SHOULD respect `Retry-After` header (min 5 seconds)

**Webhooks** (recommended for production):
```
POST /webhooks
{
  "url": "https://client.example.com/webhooks/pcb-agent",
  "events": ["job.succeeded", "job.failed", "job.cancelled"],
  "secret": "whsec_..."
}
```
- Webhook payload includes job ID, status, and result URL
- Delivery retries with exponential backoff (max 5 attempts)
- Webhook signatures using HMAC-SHA256 for verification

#### Job Timeouts

| Job Type | Max Duration | Timeout Behavior |
|----------|-------------|------------------|
| Schematic Generation | 5 minutes | Return partial + warnings |
| Placement | 10 minutes | Return best effort + score |
| Auto-Routing | 30 minutes | Return best effort + DRC report |
| DFM Analysis | 5 minutes | Complete or fail fast |
| Gerber Export | 2 minutes | Fail if files too large |

### 5.7 Versioning Strategies

#### URL Path Versioning (Primary)

```
/api/v1/projects
/api/v2/projects
```

**Rules**:
- Major versions in URL path
- Current version supported for 12 months after new major release
- Deprecation warnings in `Sunset` header for deprecated endpoints

#### Version Selection

Clients SHOULD specify desired version via URL. Optional header for content negotiation:
```
Accept-Version: v1
```

#### Breaking Change Policy

| Change Type | Version Impact | Example |
|-------------|---------------|---------|
| Remove endpoint | Major (v1 -> v2) | DELETE /v1/legacy-feature |
| Rename field | Major | `trace_width` -> `min_trace_width` |
| Change type | Major | String -> Object |
| Add field | Minor | New `impedance_tolerance` field |
| Add endpoint | Minor | New /v1/analysis endpoint |
| Bug fix | Patch | Fix calculation error |

### 5.8 Security Requirements

#### Authentication

- **OAuth 2.0** with PKCE for browser-based clients
- **API Keys** for server-to-server integrations (rotatable, scope-limited)
- **JWT Tokens** with 1-hour expiry, refresh token rotation
- **MFA Required** for Enterprise tier access

#### Authorization (RBAC)

| Role | Permissions |
|------|------------|
| **Viewer** | Read-only access to projects and outputs |
| **Designer** | Create/edit projects, run jobs, export files |
| **Admin** | Manage team, billing, API keys, audit logs |
| **Service** | Machine-to-machine, limited to specific endpoints |

#### Data Protection

- All file uploads scanned for malware before processing
- Design files encrypted at rest (AES-256)
- Transfer over TLS 1.3 only
- Customer data isolation (no co-mingling of design files)
- IP Protection: Option for on-premise deployment for sensitive designs

### 5.9 Monitoring and Observability

#### Required Metrics

| Metric | Type | Alert Threshold |
|--------|------|----------------|
| **API Latency (p99)** | Histogram | > 2 seconds |
| **Error Rate** | Counter | > 0.1% of requests |
| **Job Success Rate** | Gauge | < 95% |
| **Queue Depth** | Gauge | > 100 jobs |
| **Job Duration** | Histogram | > 150% of estimate |
| **File Processing Time** | Histogram | > 30 seconds |

#### Required Logging

- All API requests with correlation ID
- All job state transitions
- All design decisions by AI agent (for audit/debugging)
- Error stack traces (sanitized of customer data)
- Authentication events (success and failure)

#### Health Check Endpoints

```
GET /health/live     # Liveness probe (is the service running?)
GET /health/ready    # Readiness probe (can it accept traffic?)
GET /health/deep     # Deep check (database, queue, storage connectivity)
```

### 5.10 Scalability Requirements

#### Horizontal Scaling

- Stateless API servers behind load balancer
- Job workers horizontally scalable based on queue depth
- File storage via object storage (S3-compatible)
- Database read replicas for GET operations

#### Resource Limits per Job

| Resource | Limit | Reason |
|----------|-------|--------|
| **Max board size** | 600mm x 600mm | Fabricator limits |
| **Max layers** | 16 | HDI capabilities |
| **Max components** | 10,000 | Memory/processing limits |
| **Max nets** | 50,000 | Solver complexity |
| **File upload** | 500MB | Gerber sets for large designs |
| **Job output** | 1GB | Includes 3D renders and simulations |

---

## Appendix A: Quick Reference - DRC Rule Priorities

| Priority | Rule | Fix Strategy |
|----------|------|--------------|
| P0 | Short circuit | Immediate reroute |
| P0 | Unconnected net | Complete routing or flag NC |
| P0 | Clearance violation | Reroute or adjust placement |
| P1 | Annular ring < min | Increase pad size |
| P1 | Trace width < min | Widen trace or upgrade manufacturer |
| P1 | Differential mismatch | Add serpentine tuning |
| P2 | Silkscreen on pad | Clip silkscreen |
| P2 | Copper sliver | Remove or merge with pour |
| P3 | Non-optimal via | Relocate or change type |

## Appendix B: Manufacturer Capability Matrix

| Capability | JLCPCB Std | JLCPCB Adv | PCBWay Std | PCBWay Adv | OSH Park |
|------------|-----------|-----------|-----------|-----------|----------|
| Min Trace | 5mil | 3.5mil | 5mil | 3mil | 6mil |
| Min Space | 5mil | 3.5mil | 5mil | 3mil | 6mil |
| Min Drill | 0.3mm | 0.2mm | 0.2mm | 0.15mm | 0.25mm |
| Max Layers | 4 | 8 | 14 | 14 | 4 |
| Impedance Ctrl | Yes | Yes | Yes | Yes | No |
| Blind/Buried | No | Yes | Yes | Yes | No |
| HDI | No | No | Yes | Yes | No |
| Typical Cost | $ | $$ | $$ | $$$ | $ |

## Appendix C: Signal Integrity Checklist

- [ ] Identify all signals > 100 MHz or < 1ns edge rate
- [ ] Define impedance targets for each interface
- [ ] Assign proper layer stackup (signal-ground-signal-power-ground-signal for 6L)
- [ ] Route differential pairs first with tight coupling
- [ ] Match lengths within tolerance for all parallel buses
- [ ] Verify no high-speed traces cross plane splits
- [ ] Add stitching vias at all layer transitions for high-speed signals
- [ ] Run crosstalk simulation for dense parallel groups
- [ ] Verify via stubs are acceptable (or use backdrilling)
- [ ] Terminate all transmission lines appropriately

---

*End of Document*
