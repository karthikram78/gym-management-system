-- ========================================================
-- Gym Management System Database Schema & Initial Dataset
-- Database: gym_management
-- Compatible with MySQL 8.0+ / MariaDB 10.4+
-- ========================================================

CREATE DATABASE IF NOT EXISTS `gym_management`
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE `gym_management`;

-- --------------------------------------------------------
-- Table structure for `admins`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `attendance`;
DROP TABLE IF EXISTS `payments`;
DROP TABLE IF EXISTS `memberships`;
DROP TABLE IF EXISTS `members`;
DROP TABLE IF EXISTS `membership_plans`;
DROP TABLE IF EXISTS `trainers`;
DROP TABLE IF EXISTS `admins`;

CREATE TABLE `admins` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `username` VARCHAR(50) NOT NULL UNIQUE,
  `password` VARCHAR(255) NOT NULL,
  `full_name` VARCHAR(100) NOT NULL,
  `email` VARCHAR(100) NOT NULL UNIQUE,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- Table structure for `trainers`
-- --------------------------------------------------------
CREATE TABLE `trainers` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(100) NOT NULL,
  `email` VARCHAR(100) NOT NULL UNIQUE,
  `phone` VARCHAR(20) NOT NULL,
  `gender` ENUM('Male', 'Female', 'Other') NOT NULL,
  `specialization` VARCHAR(100) NOT NULL,
  `experience` INT NOT NULL DEFAULT 1,
  `salary` DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
  `joining_date` DATE NOT NULL,
  `status` ENUM('Active', 'Inactive') DEFAULT 'Active',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_trainer_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- Table structure for `membership_plans`
-- --------------------------------------------------------
CREATE TABLE `membership_plans` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `plan_name` VARCHAR(50) NOT NULL UNIQUE,
  `duration_months` INT NOT NULL,
  `price` DECIMAL(10, 2) NOT NULL,
  `description` TEXT,
  `status` ENUM('Active', 'Inactive') DEFAULT 'Active',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_plan_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- Table structure for `members`
-- --------------------------------------------------------
CREATE TABLE `members` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `full_name` VARCHAR(100) NOT NULL,
  `email` VARCHAR(100) NOT NULL UNIQUE,
  `phone` VARCHAR(20) NOT NULL,
  `gender` ENUM('Male', 'Female', 'Other') NOT NULL,
  `dob` DATE NULL,
  `address` TEXT NULL,
  `joining_date` DATE NOT NULL,
  `trainer_id` INT NULL,
  `plan_id` INT NULL,
  `membership_start` DATE NOT NULL,
  `membership_end` DATE NOT NULL,
  `status` ENUM('Active', 'Expired', 'Pending', 'Inactive') DEFAULT 'Active',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_member_status` (`status`),
  INDEX `idx_member_email` (`email`),
  INDEX `idx_member_phone` (`phone`),
  CONSTRAINT `fk_member_trainer` FOREIGN KEY (`trainer_id`) REFERENCES `trainers`(`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_member_plan` FOREIGN KEY (`plan_id`) REFERENCES `membership_plans`(`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- Table structure for `memberships` (History & Plan Logs)
-- --------------------------------------------------------
CREATE TABLE `memberships` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `member_id` INT NOT NULL,
  `plan_id` INT NULL,
  `start_date` DATE NOT NULL,
  `end_date` DATE NOT NULL,
  `amount` DECIMAL(10, 2) NOT NULL,
  `status` ENUM('Active', 'Expired', 'Cancelled') DEFAULT 'Active',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_memberships_member` (`member_id`),
  CONSTRAINT `fk_memberships_member` FOREIGN KEY (`member_id`) REFERENCES `members`(`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_memberships_plan` FOREIGN KEY (`plan_id`) REFERENCES `membership_plans`(`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- Table structure for `payments`
-- --------------------------------------------------------
CREATE TABLE `payments` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `member_id` INT NOT NULL,
  `amount` DECIMAL(10, 2) NOT NULL,
  `payment_date` DATE NOT NULL,
  `payment_method` ENUM('Cash', 'UPI', 'Card', 'Bank Transfer') NOT NULL,
  `transaction_id` VARCHAR(100) NULL,
  `status` ENUM('Paid', 'Pending', 'Failed') DEFAULT 'Paid',
  `notes` VARCHAR(255) NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_payment_date` (`payment_date`),
  INDEX `idx_payment_status` (`status`),
  CONSTRAINT `fk_payment_member` FOREIGN KEY (`member_id`) REFERENCES `members`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- Table structure for `attendance`
-- --------------------------------------------------------
CREATE TABLE `attendance` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `member_id` INT NOT NULL,
  `attendance_date` DATE NOT NULL,
  `check_in_time` TIME NULL,
  `check_out_time` TIME NULL,
  `status` ENUM('Present', 'Absent', 'Late') DEFAULT 'Present',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY `unique_daily_attendance` (`member_id`, `attendance_date`),
  INDEX `idx_att_date` (`attendance_date`),
  INDEX `idx_att_status` (`status`),
  CONSTRAINT `fk_attendance_member` FOREIGN KEY (`member_id`) REFERENCES `members`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ========================================================
-- SAMPLE DATA INSERTION
-- ========================================================

-- Default Admin Account (Username: admin, Password: admin123)
-- Password hash generated using Werkzeug scrypt/pbkdf2 or plain admin123 supported
INSERT INTO `admins` (`id`, `username`, `password`, `full_name`, `email`) VALUES
(1, 'admin', 'scrypt:32768:8:1$m9bC6j9w0Uv0oRsm$36a2a2259160d28362629676ecae0762a123689c16503c733795123d46ba1ec81e9b2520377e8a93e36e1a499d690a618e7d23d8c2aa5b642ec367e9b04fc92b', 'Master Admin', 'admin@ironpulse.com');

-- Default Membership Plans
INSERT INTO `membership_plans` (`id`, `plan_name`, `duration_months`, `price`, `description`, `status`) VALUES
(1, 'Monthly Plan', 1, 1500.00, 'Full gym access, locker room, free fitness orientation.', 'Active'),
(2, 'Quarterly Plan', 3, 4000.00, '3 months gym access + 1 complimentary body composition assessment.', 'Active'),
(3, 'Half-Yearly Plan', 6, 7000.00, '6 months gym access + 2 personal trainer consultation sessions.', 'Active'),
(4, 'Yearly Plan', 12, 12000.00, '365 days VIP access, sauna, personalized nutrition chart & towel service.', 'Active');

-- Sample Trainers
INSERT INTO `trainers` (`id`, `name`, `email`, `phone`, `gender`, `specialization`, `experience`, `salary`, `joining_date`, `status`) VALUES
(1, 'Vikram Rathore', 'vikram.trainer@ironpulse.com', '9876543210', 'Male', 'Strength & Hypertrophy', 6, 45000.00, '2023-01-15', 'Active'),
(2, 'Ananya Sharma', 'ananya.fit@ironpulse.com', '9876543211', 'Female', 'Yoga & Functional Mobility', 4, 38000.00, '2023-04-10', 'Active'),
(3, 'David Miller', 'david.crossfit@ironpulse.com', '9876543212', 'Male', 'CrossFit & Olympic Lifting', 8, 55000.00, '2022-09-01', 'Active'),
(4, 'Priya Nair', 'priya.pilates@ironpulse.com', '9876543213', 'Female', 'Pilates & Core Conditioning', 5, 42000.00, '2023-08-20', 'Active'),
(5, 'Rohan Verma', 'rohan.hiit@ironpulse.com', '9876543214', 'Male', 'HIIT & Weight Loss Coaching', 3, 35000.00, '2024-02-01', 'Active');

-- Sample Members
INSERT INTO `members` (`id`, `full_name`, `email`, `phone`, `gender`, `dob`, `address`, `joining_date`, `trainer_id`, `plan_id`, `membership_start`, `membership_end`, `status`) VALUES
(1, 'Rahul Verma', 'rahul.verma@gmail.com', '9123456780', 'Male', '1996-05-14', 'Flat 402, Skyline Heights, MG Road', '2024-01-10', 1, 4, '2024-01-10', '2025-01-10', 'Active'),
(2, 'Sneha Patel', 'sneha.patel@yahoo.com', '9123456781', 'Female', '1998-11-22', '12 Lakeview Enclave, Indiranagar', '2024-02-01', 2, 2, '2024-02-01', '2024-05-01', 'Active'),
(3, 'Arjun Reddy', 'arjun.reddy@gmail.com', '9123456782', 'Male', '1994-08-30', '77 Jubilee Hills, Phase 2', '2024-01-15', 3, 3, '2024-01-15', '2024-07-15', 'Active'),
(4, 'Kavita Sundaram', 'kavita.s@outlook.com', '9123456783', 'Female', '1992-03-18', '24 Palm Meadows, Whitefield', '2023-11-01', 4, 1, '2023-11-01', '2023-12-01', 'Expired'),
(5, 'Aditya Malhotra', 'aditya.m@gmail.com', '9123456784', 'Male', '2000-09-05', 'B-14 Green Park Ext, Sector 5', '2024-03-01', 5, 2, '2024-03-01', '2024-06-01', 'Active'),
(6, 'Pooja Hegde', 'pooja.hegde@hotmail.com', '9123456785', 'Female', '1997-07-12', 'Villa 8, Oasis Palms, Koramangala', '2024-03-10', 2, 4, '2024-03-10', '2025-03-10', 'Active'),
(7, 'Sameer Khan', 'sameer.k@gmail.com', '9123456786', 'Male', '1995-12-03', '304 Silver Crest, Bandra West', '2023-10-05', 1, 3, '2023-10-05', '2024-04-05', 'Active'),
(8, 'Tanvi Deshmukh', 'tanvi.d@gmail.com', '9123456787', 'Female', '2001-01-25', '88 Sunrise Apartments, Powai', '2024-01-05', 4, 1, '2024-01-05', '2024-02-05', 'Expired'),
(9, 'Karthik Raja', 'karthik.raja@gmail.com', '9123456788', 'Male', '1993-04-19', '15 Royal Palm Residency, Anna Nagar', '2024-02-15', 3, 4, '2024-02-15', '2025-02-15', 'Active'),
(10, 'Meera Sen', 'meera.sen@gmail.com', '9123456789', 'Female', '1999-06-11', '502 Orchid Towers, Salt Lake', '2024-03-15', NULL, 1, '2024-03-15', '2024-04-15', 'Active'),
(11, 'Nikhil Joshi', 'nikhil.joshi@gmail.com', '9123456790', 'Male', '1991-10-08', '45 Ashok Vihar, Phase 1', '2023-08-10', 1, 2, '2023-08-10', '2023-11-10', 'Expired'),
(12, 'Divya Nair', 'divya.nair@gmail.com', '9123456791', 'Female', '1995-02-17', '18 Marine Drive, Kochi', '2024-03-20', 5, 3, '2024-03-20', '2024-09-20', 'Active');

-- Sample Membership History Records
INSERT INTO `memberships` (`member_id`, `plan_id`, `start_date`, `end_date`, `amount`, `status`) VALUES
(1, 4, '2024-01-10', '2025-01-10', 12000.00, 'Active'),
(2, 2, '2024-02-01', '2024-05-01', 4000.00, 'Active'),
(3, 3, '2024-01-15', '2024-07-15', 7000.00, 'Active'),
(4, 1, '2023-11-01', '2023-12-01', 1500.00, 'Expired'),
(5, 2, '2024-03-01', '2024-06-01', 4000.00, 'Active'),
(6, 4, '2024-03-10', '2025-03-10', 12000.00, 'Active'),
(7, 3, '2023-10-05', '2024-04-05', 7000.00, 'Active'),
(8, 1, '2024-01-05', '2024-02-05', 1500.00, 'Expired'),
(9, 4, '2024-02-15', '2025-02-15', 12000.00, 'Active'),
(10, 1, '2024-03-15', '2024-04-15', 1500.00, 'Active'),
(11, 2, '2023-08-10', '2023-11-10', 4000.00, 'Expired'),
(12, 3, '2024-03-20', '2024-09-20', 7000.00, 'Active');

-- Sample Payments
INSERT INTO `payments` (`id`, `member_id`, `amount`, `payment_date`, `payment_method`, `transaction_id`, `status`, `notes`) VALUES
(1001, 1, 12000.00, '2024-01-10', 'UPI', 'UPI-240110-89324', 'Paid', 'Annual VIP membership fee'),
(1002, 2, 4000.00, '2024-02-01', 'Card', 'TXN-CARD-9921', 'Paid', 'Quarterly subscription renewal'),
(1003, 3, 7000.00, '2024-01-15', 'Bank Transfer', 'NEFT-0029104', 'Paid', 'Half yearly membership payment'),
(1004, 4, 1500.00, '2023-11-01', 'Cash', 'CASH-REC-104', 'Paid', 'Monthly plan joining fee'),
(1005, 5, 4000.00, '2024-03-01', 'UPI', 'UPI-240301-44120', 'Paid', 'Quarterly membership fee'),
(1006, 6, 12000.00, '2024-03-10', 'Card', 'TXN-CARD-7812', 'Paid', 'Full 1-year premium package'),
(1007, 7, 7000.00, '2023-10-05', 'UPI', 'UPI-231005-11029', 'Paid', 'Half-yearly plan fee'),
(1008, 8, 1500.00, '2024-01-05', 'Cash', 'CASH-REC-205', 'Paid', '1 month trial fee'),
(1009, 9, 12000.00, '2024-02-15', 'Bank Transfer', 'RTGS-240215-998', 'Paid', 'Yearly plan payment via online banking'),
(1010, 10, 1500.00, '2024-03-15', 'UPI', 'UPI-240315-77218', 'Paid', 'March monthly plan'),
(1011, 11, 4000.00, '2023-08-10', 'Card', 'TXN-CARD-4421', 'Paid', 'Quarterly fee'),
(1012, 12, 7000.00, '2024-03-20', 'UPI', 'UPI-240320-99432', 'Paid', 'Half-yearly plan fee');

-- Sample Attendance (using CURDATE() and past days to ensure dynamic today's attendance)
INSERT INTO `attendance` (`member_id`, `attendance_date`, `check_in_time`, `check_out_time`, `status`) VALUES
(1, CURDATE(), '06:30:00', '08:00:00', 'Present'),
(2, CURDATE(), '07:00:00', '08:15:00', 'Present'),
(3, CURDATE(), '07:15:00', '08:45:00', 'Present'),
(5, CURDATE(), '08:00:00', '09:30:00', 'Present'),
(6, CURDATE(), '09:00:00', NULL, 'Present'),
(7, CURDATE(), '17:30:00', '19:00:00', 'Present'),
(9, CURDATE(), '18:00:00', NULL, 'Present'),
(10, CURDATE(), '18:30:00', '20:00:00', 'Present'),
(12, CURDATE(), '19:00:00', NULL, 'Present'),
(4, CURDATE(), NULL, NULL, 'Absent'),
(8, CURDATE(), NULL, NULL, 'Absent'),
(11, CURDATE(), NULL, NULL, 'Absent');
