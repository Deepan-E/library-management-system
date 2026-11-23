
CREATE DATABASE IF NOT EXISTS library_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE library_db;

-- Drop in child-first order so the script can be re-run safely
DROP TABLE IF EXISTS issues;
DROP TABLE IF EXISTS members;
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS users;

-- ---------------------------------------------------------------------
-- 1. users : people who log in to the program (not linked to other tables)
-- ---------------------------------------------------------------------
CREATE TABLE users (
    user_id        INT           NOT NULL AUTO_INCREMENT,
    username       VARCHAR(30)   NOT NULL,
    password_hash  VARCHAR(200)  NOT NULL,          -- salted PBKDF2 hash, never the real password
    role           ENUM('ADMIN','LIBRARIAN') NOT NULL,
    PRIMARY KEY (user_id),
    UNIQUE KEY uq_users_username (username)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 2. books : catalogue and number of copies on the shelf
-- ---------------------------------------------------------------------
CREATE TABLE books (
    book_id           INT          NOT NULL AUTO_INCREMENT,
    title             VARCHAR(120) NOT NULL,
    author            VARCHAR(80)  NOT NULL,
    category          VARCHAR(50)  NOT NULL,         -- e.g. Fiction, Science
    total_copies      INT          NOT NULL,
    available_copies  INT          NOT NULL,
    PRIMARY KEY (book_id),
    CONSTRAINT chk_books_total     CHECK (total_copies >= 0),
    CONSTRAINT chk_books_available CHECK (available_copies >= 0
                                          AND available_copies <= total_copies),
    INDEX idx_books_title  (title),                  -- speeds up search by title
    INDEX idx_books_author (author)                  -- speeds up search by author
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 3. members : people allowed to borrow books
-- ---------------------------------------------------------------------
CREATE TABLE members (
    member_id  INT         NOT NULL AUTO_INCREMENT,
    full_name  VARCHAR(60) NOT NULL,
    phone      CHAR(10)    NOT NULL,
    is_active  TINYINT(1)  NOT NULL DEFAULT 1,       -- 0 = deactivated
    PRIMARY KEY (member_id),
    UNIQUE KEY uq_members_phone (phone),
    CONSTRAINT chk_members_phone  CHECK (phone REGEXP '^[0-9]{10}$'),
    CONSTRAINT chk_members_active CHECK (is_active IN (0, 1))
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 4. issues : link table, one row = one book issued to one member
--    (resolves the many-to-many between books and members)
-- ---------------------------------------------------------------------
CREATE TABLE issues (
    issue_id     INT  NOT NULL AUTO_INCREMENT,
    book_id      INT  NOT NULL,
    member_id    INT  NOT NULL,
    issue_date   DATE NOT NULL,
    due_date     DATE NOT NULL,
    return_date  DATE NULL,                           -- NULL until the book is returned
    fine_amount  INT  NOT NULL DEFAULT 0,             -- rupees
    status       ENUM('ISSUED','RETURNED') NOT NULL DEFAULT 'ISSUED',

    -- Extra helper column (allowed by the brief): equals 1 while the book is
    -- out, NULL once returned. Combined with the UNIQUE key below, it lets the
    -- database itself refuse "same member holds the same book twice".
    -- (MySQL treats NULLs as distinct, so returned rows never clash.)
    open_flag    TINYINT GENERATED ALWAYS AS (CASE WHEN status = 'ISSUED' THEN 1 ELSE NULL END) VIRTUAL,

    PRIMARY KEY (issue_id),

    CONSTRAINT fk_issues_book   FOREIGN KEY (book_id)   REFERENCES books(book_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,         -- a book that was ever issued cannot be deleted
    CONSTRAINT fk_issues_member FOREIGN KEY (member_id) REFERENCES members(member_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT chk_issues_due    CHECK (due_date >= issue_date),
    CONSTRAINT chk_issues_return CHECK (return_date IS NULL OR return_date >= issue_date),
    CONSTRAINT chk_issues_fine   CHECK (fine_amount >= 0),

    UNIQUE KEY uq_issues_one_open_copy (book_id, member_id, open_flag),
    INDEX idx_issues_member_status (member_id, status)  -- required index; also serves the member FK
) ENGINE=InnoDB;


-- =====================================================================
-- SAMPLE DATA
-- (No users are inserted: the first ADMIN is created by the program on first run.)
-- =====================================================================

INSERT INTO books (title, author, category, total_copies, available_copies) VALUES
('The God of Small Things',          'Arundhati Roy',        'Fiction',    4, 4),
('Wings of Fire',                    'A.P.J. Abdul Kalam',   'Biography',  5, 5),
('A Brief History of Time',          'Stephen Hawking',      'Science',    3, 3),
('Clean Code',                       'Robert C. Martin',     'Technology', 2, 2),
('Introduction to Algorithms',       'Thomas H. Cormen',     'Technology', 3, 3),
('The Guide',                        'R.K. Narayan',         'Fiction',    3, 3),
('Sapiens',                          'Yuval Noah Harari',    'History',    4, 4),
('Discovery of India',               'Jawaharlal Nehru',     'History',    2, 2),
('Python Crash Course',              'Eric Matthes',         'Technology', 5, 5),
('Digital Electronics',              'Morris Mano',          'Engineering',3, 3),
('Malgudi Days',                     'R.K. Narayan',         'Fiction',    2, 2),
('Cosmos',                           'Carl Sagan',           'Science',    2, 2);

INSERT INTO members (full_name, phone, is_active) VALUES
('Aarav Sharma',    '9876543210', 1),
('Priya Nair',      '9123456780', 1),
('Rahul Verma',     '9988776655', 1),
('Sneha Iyer',      '9090909090', 1),
('Karthik Raj',     '9345678901', 1),
('Meena Kumari',    '9812345670', 0);   -- deactivated, useful for testing the rule


-- =====================================================================
-- OPTIONAL: sample issue records so the three reports have data to show.
-- Delete this block if you want to start with an empty issues table.
-- Dates are relative to today, so overdue rows stay overdue.
-- =====================================================================

INSERT INTO issues (book_id, member_id, issue_date, due_date, return_date, fine_amount, status) VALUES
-- still out and OVERDUE (issued 20 days ago, due 6 days ago)
(1, 1, CURDATE() - INTERVAL 20 DAY, CURDATE() - INTERVAL 6 DAY,  NULL, 0, 'ISSUED'),
(4, 2, CURDATE() - INTERVAL 25 DAY, CURDATE() - INTERVAL 11 DAY, NULL, 0, 'ISSUED'),
-- still out, NOT overdue
(9, 3, CURDATE() - INTERVAL 3 DAY,  CURDATE() + INTERVAL 11 DAY, NULL, 0, 'ISSUED'),
-- returned late (5 days late x Rs 2 = Rs 10)
(2, 1, CURDATE() - INTERVAL 30 DAY, CURDATE() - INTERVAL 16 DAY, CURDATE() - INTERVAL 11 DAY, 10, 'RETURNED'),
-- returned on time
(9, 4, CURDATE() - INTERVAL 40 DAY, CURDATE() - INTERVAL 26 DAY, CURDATE() - INTERVAL 30 DAY, 0,  'RETURNED'),
(1, 5, CURDATE() - INTERVAL 50 DAY, CURDATE() - INTERVAL 36 DAY, CURDATE() - INTERVAL 40 DAY, 0,  'RETURNED'),
(9, 2, CURDATE() - INTERVAL 60 DAY, CURDATE() - INTERVAL 46 DAY, CURDATE() - INTERVAL 44 DAY, 0,  'RETURNED');

-- Keep available_copies consistent with the copies currently out
-- (books 1, 4 and 9 each have one copy out).
UPDATE books SET available_copies = available_copies - 1 WHERE book_id IN (1, 4, 9);
