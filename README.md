# class-tracking-platform

The purpose of this application is to:
1. Streamline the generation of reports used to track student progress in small class/turoring settings - daily class summaries, homework assignments, and progress reports.
2. Streamline the assignment of students to new classes upon conclusion of a term. 
3. Introduce a hierarchical, JSON backed domain model for class, student, and teacher data persisted in Amazon S3.

The application requires 3 starting data stores per organization: 
1. Student Data: An .xlsx spreadsheet containing a column with student names, teachers' names, and level in the respective curriculum. The spreadsheet must separate each class of students with a newlines.
2. Curriculum Data: An .xlsx spreasheet containing a column with curriculum levels, sublevels (if applicable), lesson numbers, homework, and reading corresponding to a particular lesson number.
3. Class Summary Template: A .word document with newlines between section headers. 

**To register your educational organization in the platform:**
Under construction. 
