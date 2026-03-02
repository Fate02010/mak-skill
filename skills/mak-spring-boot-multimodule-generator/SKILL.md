---
name: spring-boot-multimodule-generator
description: >
  Use when the user asks to generate/create/scaffold a Spring Boot multi-module Maven project OR add/create Maven modules in an existing project.
  适用于：创建 Spring Boot 多模块 Maven 项目，或在已有项目中新增/创建模块（module）。
  Keywords: create project/创建项目, scaffold/脚手架, generator/生成器, template/模板, multi-module/多模块, module/模块, add module/新增模块,
  Maven/maven 多模块, Spring Boot 2.x/3.x, Java 17/21, JDK17/JDK21, ORM: MyBatis/MyBatis-Plus/JPA/Hibernate, Redis/缓存,
  DB: MySQL/PostgreSQL/PG/PGSQL/MariaDB.
---

# 1. Purpose
This skill can:
- **Create a new Spring Boot multi-module Maven project** (interactive choices).
- **Add new Maven modules** to an **existing** multi-module project (interactive module selection).
- Generate consistent parent `dependencyManagement`, module POMs, and minimal wiring (depending on selected ORM/DB/Redis).

# 2. Triggers (When to Use)
Use when user asks for:
- Create/generate/scaffold a Spring Boot multi-module Maven project (创建/生成/脚手架/多模块项目)
- Add/create a module in an existing Maven multi-module project (新增模块/创建module/添加子模块)
- Standard options selection: Java 17/21, Boot 2.x/3.x, ORM, Redis, DB driver

# 3. Non-triggers (When NOT to Use)
Do NOT use when:
- Concept-only discussion (no file generation)
- User does not allow file creation/modification
- The repository is not a Maven multi-module project and user only wants a single-module quick demo (use other skill)

# 4. Inputs (Interactive Questionnaire)
Before modifying files, ask ONE questionnaire and wait for answers.

## 4.1 Mode Selection (Must Ask)
- 0) Mode:  
  1) Create new project (创建新项目)  
  2) Add modules to existing project (在已有项目里新增模块)

## 4.2 Create New Project (Mode 1) - Required Questions
1) groupId:
2) artifactId (root project folder name):
3) basePackage (default = groupId):
4) Java: 1) 17  2) 21
5) Spring Boot: 1) 2.x  2) 3.x (optional: specify exact version)
6) ORM: 1) MyBatis (default MyBatis-Plus) 2) JPA 3) Hibernate
7) DB: 1) MySQL 2) PostgreSQL 3) MariaDB
8) Redis: enabled by default (say "disable" to disable)

### 4.2.1 Module Plan (Mode 1) - Interactive Module Set
Ask user to choose a module template set (default recommended), OR custom list.

- A) Recommended DDD (default):
  - common, domain, infrastructure, application, interfaces, bootstrap
- B) Minimal practical (simpler):
  - common, infrastructure, interfaces, bootstrap
- C) Custom (user lists module names)

If user chooses C, ask:
- List module names (comma-separated)
- Identify the runtime module (default = bootstrap)
- Identify web module (default = interfaces)

## 4.3 Add Modules (Mode 2) - Required Questions
1) Root module/pom location:
- Where is the parent `pom.xml`? (default: repo root `pom.xml`)
2) Existing module names (if unknown, skill must detect from parent POM `<modules>`):
- Allow skill to parse and list them, then confirm.
3) Add which modules:
- User chooses from templates or provides custom names:
  - common / domain / infrastructure / application / interfaces / bootstrap / bom
  - or custom module name(s)
4) Module type for each new module:
- 1) library (jar)
- 2) spring-boot app (runtime module)
5) Dependencies per new module (minimal):
- If runtime/web: include `spring-boot-starter-web` (optional)
- If infra: include ORM + DB driver + Redis config modules where appropriate

# 5. Workflow (Must Follow)
1) Ask the questionnaire (Mode + required options)
2) Inspect repository context:
   - If Mode 2, read parent POM and list existing modules
3) Propose changes:
   - Print planned directory tree and which files will be created/changed
4) Generate/Modify files:
   - Create module folders, module POMs
   - Update parent POM `<modules>` (Mode 2) and align `dependencyManagement`
   - Add minimal Spring Boot bootstrap module if requested
5) Provide verification commands:
   - `mvn -q -DskipTests package`
   - run command for runtime module if applicable
6) Summarize:
   - Selected options, generated modules, key files, next steps

# 6. Module Rules (How to Create Modules)
## 6.1 Parent POM Update
- When adding modules, update `<modules>` in parent `pom.xml`.
- Keep module ordering stable and readable (e.g., common → domain → infra → app → interfaces → bootstrap).

## 6.2 Module POM Conventions
Each module must:
- Inherit from parent (`<parent>`)
- Use consistent `artifactId` naming:
  - `<root-artifactId>-<module>` OR simply `<module>` (choose one convention and apply consistently)
- Depend on other modules by responsibility:
  - application depends on domain + common
  - infrastructure depends on domain + common (+ ORM/DB/Redis deps)
  - interfaces depends on application + common
  - bootstrap depends on interfaces (+ spring-boot starters)

## 6.3 Runtime Module (Spring Boot app)
- Only the runtime module should include `spring-boot-maven-plugin`.
- Provide:
  - `@SpringBootApplication` main class
  - `application.yml` minimal config

# 7. Dependency Management Requirements
Parent must include:
- `dependencyManagement` importing `spring-boot-dependencies`
- Optionally align/override Spring Framework versions if org requires
- `pluginManagement` for compiler plugin and boot plugin

Child modules should not declare core Spring/Boot versions directly.

# 8. Dependencies (Based on Choices)
- ORM (MyBatis/MyBatis-Plus/JPA/Hibernate)
- Redis (default on)
- DB driver (MySQL/PostgreSQL/MariaDB)
- Keep Boot 2 vs Boot 3 namespace consistency (javax vs jakarta).

# 9. Output Format (Must)
Final output must include:
- What mode was executed (Mode 1 or Mode 2)
- Planned vs created module tree
- Parent POM changes summary (modules added, dependencyManagement)
- Key files list
- Build/run commands

# 10. Quality Bar (DoD)
- `mvn -q -DskipTests package` succeeds
- New modules are correctly included in parent `<modules>`
- If runtime module exists, it can start or at least compiles with proper plugin config
- DependencyManagement is not duplicated across modules

# 11. Interactive Questionnaire Template (Ask Exactly Like This)
0) Mode:
   1) Create new project (创建新项目)
   2) Add modules to existing project (新增模块)

If Mode 1:
- ① groupId:
- ② artifactId:
- ③ basePackage (default = groupId):
- ④ Java: 1) 17  2) 21
- ⑤ Spring Boot: 1) 2.x  2) 3.x (optional exact version)
- ⑥ ORM: 1) MyBatis (default MyBatis-Plus) 2) JPA  3) Hibernate
- ⑦ DB: 1) MySQL  2) PostgreSQL  3) MariaDB
- ⑧ Redis: enabled by default (say "disable" if you want to disable)
- ⑨ Module set:
    A) Recommended DDD (common, domain, infrastructure, application, interfaces, bootstrap)
    B) Minimal (common, infrastructure, interfaces, bootstrap)
    C) Custom (provide module names)

If Mode 2:
- ① Parent pom.xml path (default: ./pom.xml):
- ② Add modules (choose: common/domain/infrastructure/application/interfaces/bootstrap/bom or custom names):
- ③ For each new module: type 1) library 2) runtime app
- ④ Redis: enabled by default (say "disable" if you want to disable)