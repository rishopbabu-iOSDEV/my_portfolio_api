# API views (`11_api_views.sql`)

Course 5, Module 4 (Lab B). These are the seven views the API reads from.

```sql
-- =====================================================================
-- 11_api_views.sql
-- Course 5, Module 4 (Lab B): the API views.
--
-- One view per public section of the resume.json contract. Each view's
-- columns are EXACTLY the contract's keys (version 2: with id / project_id),
-- so on Day 3 every public GET endpoint is one SELECT.
--
-- Data, not display: ISO dates and raw numbers (unlike the Course 4 report
-- views, which format "Jun 2021 - May 2026"). Both kinds stay.
-- No ORDER BY in a view: the API applies the sort parameter.
-- No private data: no email, and no contact messages, in any view that
-- portfolio_web can read.
--
-- Run as root, after the rebuild:
--   01 -> 02 -> 02a -> 03 -> 06 -> 09 (Part C) -> 11_api_views.sql
-- Re-runnable: CREATE OR REPLACE VIEW; GRANT can be repeated.
-- =====================================================================

USE future_portfolio_db;

-- ---------------------------------------------------------------------
-- 1. Profile: one row, four columns. NOT email.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_api_profile AS
SELECT p.full_name,
       p.headline,
       p.location,
       p.professional_summary AS summary
FROM people AS p
WHERE p.person_id = 1;

-- ---------------------------------------------------------------------
-- 2. Summary: one row (Course 4's v_career_summary, contract keys)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_api_summary AS
SELECT (SELECT COUNT(*) FROM companies) AS companies,
       (SELECT COUNT(*) FROM roles)     AS roles,
       (SELECT COUNT(*) FROM projects)  AS projects,
       (SELECT COUNT(*) FROM skills)    AS skills,
       (SELECT COUNT(*) FROM awards)    AS awards,
       (SELECT SUM(TIMESTAMPDIFF(MONTH, e.start_date, e.end_date) + 1) / 12
        FROM employment AS e)           AS career_years;

-- ---------------------------------------------------------------------
-- 3. Experience: one row per role; id = role_id
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_api_experience AS
SELECT r.role_id      AS id,
       c.company_name AS company,
       r.role_title   AS role,
       r.start_date,
       r.end_date,
       r.team_size
FROM roles      AS r
JOIN employment AS e ON e.employment_id = r.employment_id
JOIN companies  AS c ON c.company_id    = e.company_id;

-- ---------------------------------------------------------------------
-- 4. Projects: one row per role-project pair (18), with a JSON array of
--    skills. project_id, not id: a project delivered by two roles
--    appears twice, so project_id is not unique in this view.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_api_projects AS
SELECT p.project_id,
       p.project_name AS project,
       r.role_title   AS role,
       c.company_name AS company,
       (SELECT JSON_ARRAYAGG(s.skill_name)
        FROM project_skills AS ps
        JOIN skills AS s ON s.skill_id = ps.skill_id
        WHERE ps.project_id = p.project_id) AS skills
FROM projects      AS p
JOIN role_projects AS rp ON rp.project_id   = p.project_id
JOIN roles         AS r  ON r.role_id       = rp.role_id
JOIN employment    AS e  ON e.employment_id = r.employment_id
JOIN companies     AS c  ON c.company_id    = e.company_id;

-- ---------------------------------------------------------------------
-- 5. Skills with their evidence count (LEFT JOIN: 0 for unused skills)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_api_skills AS
SELECT s.skill_id          AS id,
       s.skill_name        AS skill,
       s.skill_category    AS category,
       COUNT(ps.project_id) AS project_count
FROM skills              AS s
LEFT JOIN project_skills AS ps ON ps.skill_id = s.skill_id
GROUP BY s.skill_id, s.skill_name, s.skill_category;

-- ---------------------------------------------------------------------
-- 6. Education: years as numbers; the page decides how to show them
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_api_education AS
SELECT ed.education_id   AS id,
       ed.qualification,
       ed.institution,
       ed.education_type AS type,
       ed.start_year,
       ed.end_year
FROM education AS ed;

-- ---------------------------------------------------------------------
-- 7. Awards
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_api_awards AS
SELECT a.award_id       AS id,
       a.award_name     AS award,
       a.awarding_body  AS awarded_by,
       a.award_year     AS year,
       a.award_category AS category
FROM awards AS a;

-- ---------------------------------------------------------------------
-- Grants: SELECT on each view, to the read-only API user. Never on a table.
-- ---------------------------------------------------------------------
GRANT SELECT ON future_portfolio_db.v_api_profile    TO 'portfolio_web'@'localhost';
GRANT SELECT ON future_portfolio_db.v_api_summary    TO 'portfolio_web'@'localhost';
GRANT SELECT ON future_portfolio_db.v_api_experience TO 'portfolio_web'@'localhost';
GRANT SELECT ON future_portfolio_db.v_api_projects   TO 'portfolio_web'@'localhost';
GRANT SELECT ON future_portfolio_db.v_api_skills     TO 'portfolio_web'@'localhost';
GRANT SELECT ON future_portfolio_db.v_api_education  TO 'portfolio_web'@'localhost';
GRANT SELECT ON future_portfolio_db.v_api_awards     TO 'portfolio_web'@'localhost';

SHOW GRANTS FOR 'portfolio_web'@'localhost';

-- ---------------------------------------------------------------------
-- Checks: run these connected as portfolio_web (section 7 of the Markdown)
-- ---------------------------------------------------------------------
-- SELECT COUNT(*) FROM v_api_awards WHERE category = 'Industry';          -- 7
-- SELECT COUNT(*) FROM v_api_awards WHERE year >= 2020;                   -- 7
-- SELECT COUNT(*) FROM v_api_experience WHERE company = 'CloudHarbor Software'; -- 4
-- SELECT id, skill FROM v_api_skills WHERE project_count = 0;             -- skills 2 and 17
-- SELECT * FROM v_api_profile;                                            -- 1 row, 4 columns
-- SELECT email FROM people;                                               -- Error 1142
```
