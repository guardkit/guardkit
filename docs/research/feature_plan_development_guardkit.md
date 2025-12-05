# Feature Plan Development (FPD) — GuardKit Methodology

## 1. Concise Definition
Feature Plan Development (FPD) is a methodology where every new capability begins with an AI‑generated **Feature Plan** that defines structure, subtasks, parallel‑wave execution, documentation, and implementation flow.  
A single `/feature-plan` command produces a complete, consistent, execution-ready feature workspace.

---

## 2. Extended Definition
FPD treats **features as the unit of planning** and **tasks as the unit of execution**.  
It uses GuardKit’s AI‑orchestrated planning pipeline to automatically generate:

- Feature review task  
- High‑resolution feature plan  
- Subtask decomposition  
- Parallel‑safe wave ordering  
- Implementation guides  
- Workspace folder structure  

FPD is iterative, automation-friendly, and designed for agent-native workflows.

---

## 3. FPD Principles
1. **Feature-first planning**  
2. **AI-assisted structure, human judgment**  
3. **Consistent artefacts, reproducible outputs**  
4. **Parallel-safe execution by design**  
5. **Progressive automation**  
6. **Tasks remain flexible, granular units of work**  
7. **Plans become the source of truth**  
8. **Feature workspaces isolate scope**  
9. **Quality gates built-in, not bolted on**  
10. **Features ship only after validated plan + executed tasks**

---

## 4. FPD Manifesto (Short Version)
**We value:**

- **Features over files**  
- **Plans over improvisation**  
- **Structured decomposition over ad‑hoc tasking**  
- **Parallel execution over sequential bottlenecks**  
- **Automation where possible, human oversight where needed**

**While there is value in the items on the right,  
we embrace the left as the foundation of Feature Plan Development.**

---

## 5. Branding-Friendly README Manifesto
### **The Feature Plan Development Manifesto**
Feature Plan Development (FPD) is the foundation of GuardKit’s workflow philosophy.

We believe that:

- Every capability deserves a clear Feature Plan  
- AI excels at generating structured, repeatable plans  
- Developers do their best work when guided, not constrained  
- Consistency is a feature, not a chore  
- Automation should grow naturally from solid planning  
- Parallel execution should be safe, predictable, and conflict-aware  

GuardKit empowers teams to start every feature with a single command  
and ship with confidence.

---

## 6. Tagline for GuardKit
**“Plan Features. Build Faster.”**

(Alternatives:  
- *“One command. One plan. One feature at a time.”*  
- *“Feature-first AI development.”*)

---

## 7. Suggested Edits for `redeem.md` to Introduce FPD

### Add to the top section:
> GuardKit is built on the **Feature Plan Development (FPD)** methodology:  
> a feature-first workflow where a single `/feature-plan` command generates a complete, consistent plan, subtask breakdown, and implementation workspace.  
> FPD ensures that every change—large or small—follows a predictable, structured, high-quality process.

### Add to the Workflow section:
> ### Feature Plan Development Integration  
> When working on new capabilities, GuardKit recommends starting with:  
> ```
> /feature-plan "your feature name"
> ```  
> This produces a full Feature Plan, folder structure, subtasks, and implementation guide, ensuring your work aligns with GuardKit’s automation pipeline and quality gates.

### Add to concluding section:
> FPD brings reproducibility, automation readiness, and parallel-safe task execution to GuardKit’s development lifecycle.

---

