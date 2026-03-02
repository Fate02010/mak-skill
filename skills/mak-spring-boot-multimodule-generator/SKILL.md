---
name: spring-boot-multimodule-generator
description: >
  Use when the user asks to generate/create/scaffold a Spring Boot Maven project OR add/create Maven modules in an existing project,
  with interactive choices (Java 17/21, Spring Boot 2.x/3.x, ORM: MyBatis(+MyBatis-Plus)/JPA/Hibernate, Redis, DB drivers: MySQL/PostgreSQL/MariaDB).
  This skill keeps Maven modules minimal and technology-oriented; DDD layers are packages inside the business module (no domain/application/interfaces/infrastructure modules).
  适用于：创建 Spring Boot Maven 项目或在已有项目中新增模块（module），并进行交互式选择（Java 17/21、Boot 2/3、ORM、Redis、DB）。
  关键字/keywords: create project/创建项目, scaffold/脚手架, generator/生成器, template/模板, multi-module/多模块, module/模块, add module/新增模块,
  Maven/maven 多模块, Spring Boot 2.x/3.x, Java 17/21, JDK17/JDK21, ORM: MyBatis/MyBatis-Plus/JPA/Hibernate, Redis/缓存,
  DB: MySQL/PostgreSQL/PG/PGSQL/MariaDB.
---

# 1. Purpose
Generate a **Spring Boot Maven project** and/or **add Maven modules** to an existing project via an **interactive questionnaire**.

Key design choices:
- Maven modules are **minimal and technology-oriented** (e.g., `common`, `app`, `starter`, optional `bom`).
- DDD layers (**domain/application/interfaces/infrastructure**) are created as **packages inside the business module** (default `app`), NOT as separate Maven modules.

# Global Rule: Always Ask Module Names
For both Mode 1 (Create new project) and Mode 2 (Add modules), the wizard MUST ask for module names.
- Even if the user chooses a preset module set/template (Recommended/Minimal/Starter-only/Custom), still ask to confirm or rename modules.
- Provide defaults and allow pressing Enter to accept defaults.
- Validate names as Maven-friendly: lowercase letters, digits, and hyphens only (`[a-z0-9-]+`).

# 2. Triggers (When to Use)
Use this skill when the user requests any combination of:
- Create/generate/scaffold a Spring Boot Maven project (创建/生成/脚手架/模板项目)
- Create/add Maven module(s) in an existing multi-module project (新增模块/添加子模块/创建 module)
- Interactive selection of Java 17/21, Spring Boot 2.x/3.x, ORM, Redis, and DB drivers

# 3. Non-triggers (When NOT to Use)
Do NOT use this skill when:
- The user asks only conceptual questions without requesting file generation
- The user does not allow creating/modifying files
- The user requests a full business system beyond scaffolding
- The target is not Maven (e.g., Gradle-only) unless the user explicitly asks to adapt

# 4. Guardrails (Safety & Control)
- This skill SHOULD be invoked explicitly (e.g., `$spring-boot-multimodule-generator`) for safety, because it may create many files.
- Never paste or generate secrets (tokens/passwords/private keys).
- Do not run destructive commands (e.g., `rm -rf`) or mass refactors beyond the agreed scope.
- Prefer small, reviewable changes: produce a plan and file list before writing many files.

# 5. Inputs (Interactive Questionnaire)
Before generating/modifying any files, ask ONE questionnaire and wait for answers.

## 5.1 Mode Selection (Must Ask)
0) Mode:
1) Create new project (创建新项目)
2) Add modules to existing project (在已有项目里新增模块)

## 5.2 Mode 1: Create New Project (Required Questions)
1) `groupId`
2) `artifactId` (also used as root folder name)
3) `basePackage` (default = groupId)
4) Java: 1) 17  2) 21
5) Spring Boot: 1) 2.x  2) 3.x (optional: exact version)
6) ORM: 1) MyBatis (default MyBatis-Plus)  2) JPA  3) Hibernate
7) DB: 1) MySQL  2) PostgreSQL  3) MariaDB
8) Redis: enabled by default (say "disable" to disable)

### 5.2.1 Module Set (Mode 1)
Choose a module set. DDD layers will be generated as **packages inside `app`**.

- A) Recommended (default): `common`, `app`, `starter`
- B) Minimal: `app`, `starter`
- C) Custom: user provides module names (must identify business module and optional runtime module)
- D) Starter-only (single module): `starter` only (DDD packages live inside `starter`)

If C, ask:
- Module names (comma-separated)
- Which is the business module? (default = `app`)
- Which is the runtime module? (default = `starter`, optional)

#### Starter-only Rules
If module set is **D) Starter-only**:
- Create a single Maven module named `starter` (or user-provided name).
- The module is both **business module** and **runtime module**.
- Generate DDD packages under `starter/src/main/java/<basePackage>/`:
  - `domain/`, `application/`, `interfaces/`, `infrastructure/`
- Parent POM may still exist as the root project POM (single-module), but do NOT create additional child modules.

## 5.3 Mode 2: Add Modules to Existing Project (Required Questions)
1) Parent `pom.xml` path (default: `./pom.xml`)
2) Add which modules:
   - choose from `common`, `app`, `starter`, `bom`, or custom module names
3) For each new module: type
   - 1) library (`jar`)
   - 2) runtime app (Spring Boot runnable module)
4) Redis: enabled by default (say "disable" to disable)
5) If adding a business module: confirm the `basePackage` (or derive from existing code)

# 6. Workflow (Wizard-style, Step-by-step)

1) Start Wizard
   - Explain that the skill will collect options step-by-step and will NOT create files until final confirmation.

2) Step-by-step collection
   - Ask ONE question per step (or one tightly-related group).
   - After each answer, print a short "Summary so far".

3) Validation & defaults
   - Validate user input (e.g., mode=1/2, Java=17/21, Boot=2.x/3.x).
   - Apply safe defaults when user does not specify details (e.g., Redis enabled by default).

4) Preflight Plan (no file changes yet)
   - Print:
     - planned module tree
     - DDD package layout (inside business module)
     - files to be created/modified
     - build/run commands
   - Highlight risky operations (e.g., modifying parent pom.xml).

5) Final Confirmation (required)
   - Ask the user to type `CONFIRM` to proceed.
   - If user does not confirm, stop after showing the plan.

6) Execute changes
   - Create/modify files as planned.

7) Verify & Summarize
   - Provide verification commands and a concise summary of what was generated.

# 7. Project Structure (Modules vs Packages)

## 7.1 Default Modules (Minimal, technology-oriented)
Recommended default modules:
- `<root>`: parent aggregator (`packaging=pom`)
- `common` (optional): shared utilities, common response objects, exceptions, constants
- `app`: main business module (`packaging=jar`), contains DDD layers as packages
- `starter`: runtime Spring Boot module (`packaging=jar`), contains `@SpringBootApplication`, depends on `app` (and `common`)

Optional:
- `bom`: centralized dependencyManagement module if the org prefers an explicit BOM module; otherwise keep dependencyManagement in parent.

## 7.2 DDD Layers as Packages (Inside Business Module)
Inside `app/src/main/java/<basePackage>/`, create:
- `domain/` (entities, value objects, domain services, domain events)
- `application/` (application services, use cases, command/query models)
- `interfaces/` (controllers, web DTOs, request/response, API adapters)
- `infrastructure/` (persistence adapters, repositories/mappers, Redis config, external clients)

Important:
- Do NOT create Maven modules named `domain`, `application`, `interfaces`, or `infrastructure`.
- These are packages under the business module.

## 7.3 Starter-only (Single Module) Option
When Starter-only is chosen:
- Create only one module (user-named; default `starter`).
- This module is both **business module** and **runtime module**.
- DDD layers are packages inside this module:
  - `<basePackage>.domain`
  - `<basePackage>.application`
  - `<basePackage>.interfaces`
  - `<basePackage>.infrastructure`

# 8. Maven & Dependency Management Requirements
The parent POM MUST include:
- `dependencyManagement`
  - Import `spring-boot-dependencies` BOM
  - If the user explicitly requires controlling Spring Framework versions, optionally align via a Spring Framework BOM or properties (without breaking the Boot BOM).
- `pluginManagement`
  - `maven-compiler-plugin` (source/target = 17 or 21)
  - `spring-boot-maven-plugin` (configured so it runs only in the runtime module)

Child modules MUST:
- Inherit from the parent
- Avoid declaring Spring/Boot dependency versions directly; rely on `dependencyManagement`

# 9. Module Rules (How to Create/Add Modules)

## 9.1 Parent POM `<modules>` Update (Mode 2)
- When adding modules, update `<modules>` in parent `pom.xml`.
- Keep module ordering stable/readable (e.g., `common` → `app` → `starter`).

## 9.2 Module Naming Convention
Pick one convention and apply consistently:
- Convention A: `<root-artifactId>-<module>` (e.g., `demo-platform-app`)
- Convention B: `<module>` (e.g., `app`, `starter`)

## 9.3 Module Name Validation (MUST)
- Allowed pattern: `[a-z0-9-]+`
- Disallow: spaces, uppercase, underscores, dots, non-ASCII characters
- Names must be unique within the project
- If invalid/conflicting, ask the user to rename before generating files

## 9.4 Inter-module Dependencies
- `app` depends on `common` (if present)
- `starter` depends on `app` (and `common` if present)
- `common` should avoid Spring Boot starters unless explicitly required

## 9.5 Runtime Module (`starter`) Requirements
Only the runtime module should:
- Apply/execute `spring-boot-maven-plugin`
- Contain `@SpringBootApplication` main class
- Provide `application.yml` with minimal configuration

# 10. Dependencies (Based on Choices)

## 10.1 Spring Boot 2.x vs 3.x
- Boot 2.x: beware of `javax.*` vs `jakarta.*` differences
- Boot 3.x: uses `jakarta.*` namespaces
Generated dependencies/config must match the chosen Boot line (do not mix `javax` and `jakarta`).

## 10.2 ORM
- MyBatis: `mybatis-spring-boot-starter`
- MyBatis-Plus (default when MyBatis selected): `mybatis-plus-boot-starter`
- JPA: `spring-boot-starter-data-jpa`
- Hibernate: prefer via JPA starter (Hibernate is the default provider). If user explicitly requests “pure Hibernate”, add notes/config guidance.

## 10.3 Redis (Enabled by Default)
- `spring-boot-starter-data-redis`
- Provide minimal `application.yml` examples (host/port/password/database/timeout)

## 10.4 DB Drivers (One of)
- MySQL: `mysql-connector-j`
- PostgreSQL: `org.postgresql:postgresql`
- MariaDB: `org.mariadb.jdbc:mariadb-java-client`

# 11. Output Format (Must)
Final output MUST include:
1) Mode executed (Mode 1 or Mode 2)
2) Planned vs created module tree
3) Parent POM change summary (modules added/updated, dependencyManagement highlights)
4) Key file list (parent `pom.xml`, each module `pom.xml`, runtime `application.yml`, main class)
5) Build/run commands
6) Summary of selected options (Java/Boot/ORM/DB/Redis)

## Wizard UI Convention (recommended)
At each step:
- Show choices with numbers/letters
- Accept short answers (e.g., "1", "A", "disable")
- Print "Summary so far" after the user answers

# 12. Quality Bar (Definition of Done)
- `mvn -q -DskipTests package` succeeds
- New modules appear in parent `<modules>` (Mode 2)
- Child modules do not re-declare core Spring/Boot versions unnecessarily
- If `starter` exists: it at least compiles and provides a runnable entrypoint (`spring-boot:run` command)
- Dependencies/config are consistent with Boot 2 vs Boot 3 namespace requirements

# 13. Wizard Steps (Ask Step-by-step)

## Step 0: Mode
Ask:
- Choose mode:
  1) Create new project (创建新项目)
  2) Add modules to existing project (新增模块)

Then print:
- Summary so far: mode = ...

---

## Mode 1 Wizard (Create new project)

### Step 1: Project coordinates
Ask:
- groupId:
- artifactId:
- basePackage (default = groupId)

### Step 2: Java version
Ask:
- Java:
  1) 17
  2) 21

### Step 3: Spring Boot line
Ask:
- Spring Boot:
  1) 2.x
  2) 3.x
- Optional: exact version (press Enter to skip)

### Step 4: ORM
Ask:
- ORM:
  1) MyBatis (default MyBatis-Plus)
  2) JPA
  3) Hibernate
If MyBatis selected:
- Enable MyBatis-Plus?
  1) Yes (default)
  2) No

### Step 5: Database
Ask:
- DB:
  1) MySQL
  2) PostgreSQL
  3) MariaDB

### Step 6: Redis
Ask:
- Redis:
  1) Enable (default)
  2) Disable

### Step 7: Choose module template (count/intent)
Ask:
- Module template:
  A) Recommended: 3 modules (common + business + runtime)
  B) Minimal: 2 modules (business + runtime)
  C) Starter-only: 1 module (runtime only)
  D) Custom: provide your own module names

### Step 8: Module names (ALWAYS REQUIRED)
Ask module names (defaults shown; user may rename):
- If A) Recommended:
  - Common module name (default: `common`)
  - Business module name (default: `app`)
  - Runtime module name (default: `starter`)
- If B) Minimal:
  - Business module name (default: `app`)
  - Runtime module name (default: `starter`)
- If C) Starter-only:
  - Runtime module name (default: `starter`) *(this is also the business module)*
- If D) Custom:
  - Module names (comma-separated)
  - Which is the business module? (required)
  - Which is the runtime module? (optional; if provided, it must depend on business)

Validate module names using `[a-z0-9-]+` and ensure uniqueness.


### Step 9: Preflight plan + confirmation
Print planned:
- module tree (with final module names)
- package layout inside business module:
  - `domain/`, `application/`, `interfaces/`, `infrastructure/`
- list of files to create/modify
- build/run commands
Then ask:
- Type `CONFIRM` to generate files, or anything else to cancel.

---

## Mode 2 Wizard (Add modules to existing project)

### Step 1: Parent POM location
Ask:
- Parent pom.xml path (default: ./pom.xml)

### Step 2: Detect existing modules
Action:
- Parse parent POM <modules> and print detected modules
Ask:
- Confirm detected module list (Y/N). If N, ask user to provide correct module list.

### Step 3: Choose what to add (template or custom)
Ask:
- Add modules by template:
  A) Add common + business + runtime
  B) Add business + runtime
  C) Add runtime only
  D) Custom selection (comma-separated module names)

### Step 4: New module names (ALWAYS REQUIRED)
Ask for the exact names of the modules to be added (defaults shown; user may rename):
- If A) template:
  - Common module name (default: `common`)
  - Business module name (default: `app`)
  - Runtime module name (default: `starter`)
- If B) template:
  - Business module name (default: `app`)
  - Runtime module name (default: `starter`)
- If C) template:
  - Runtime module name (default: `starter`)
- If D) custom:
  - Provide module names (comma-separated)
  - Identify which is runtime module (optional; recommended)

### Step 5: Module type mapping
Ask:
- For each new module, choose type:
  1) library (jar)
  2) runtime app (Spring Boot runnable)
If user selects a runtime module, ensure only one module is configured to execute `spring-boot-maven-plugin`.

### Step 6: basePackage (if needed)
Ask:
- basePackage (only if adding a new business module or no existing basePackage can be inferred)

### Step 7: Redis
Ask:
- Redis:
  1) Enable (default)
  2) Disable

### Step 8: Preflight plan + confirmation
Print planned changes:
- parent pom.xml changes
- module tree after changes (with final module names)
- files to create/modify
- build/run commands
Ask:
- Type `CONFIRM` to proceed.