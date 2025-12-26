-- 테이블 구조 백업
-- 생성일: 2025-12-22 14:34:37.576569+00:00

SET FOREIGN_KEY_CHECKS=0;

-- Table structure for table `accounts_inquiry`
DROP TABLE IF EXISTS `accounts_inquiry`;
CREATE TABLE `accounts_inquiry` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `category` varchar(20) NOT NULL,
  `title` varchar(200) NOT NULL,
  `content` longtext NOT NULL,
  `status` varchar(20) NOT NULL,
  `admin_response` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `answered_at` datetime(6) DEFAULT NULL,
  `answered_by_id` bigint DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `accounts_inquiry_answered_by_id_48f64c10_fk_accounts_user_id` (`answered_by_id`),
  KEY `accounts_in_user_id_ba6a9d_idx` (`user_id`),
  KEY `accounts_in_status_b3a7cf_idx` (`status`),
  KEY `accounts_in_created_fa689f_idx` (`created_at` DESC),
  CONSTRAINT `accounts_inquiry_answered_by_id_48f64c10_fk_accounts_user_id` FOREIGN KEY (`answered_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `accounts_inquiry_user_id_aff3d7e4_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `accounts_report`
DROP TABLE IF EXISTS `accounts_report`;
CREATE TABLE `accounts_report` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `report_type` varchar(20) NOT NULL,
  `target_id` int unsigned NOT NULL,
  `reason` longtext NOT NULL,
  `status` varchar(20) NOT NULL,
  `admin_note` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `processed_at` datetime(6) DEFAULT NULL,
  `processed_by_id` bigint DEFAULT NULL,
  `reporter_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `accounts_report_processed_by_id_5d383234_fk_accounts_user_id` (`processed_by_id`),
  KEY `accounts_re_reporte_8da0cd_idx` (`reporter_id`),
  KEY `accounts_re_report__eda831_idx` (`report_type`,`target_id`),
  KEY `accounts_re_status_859365_idx` (`status`),
  KEY `accounts_re_created_08a081_idx` (`created_at` DESC),
  CONSTRAINT `accounts_report_processed_by_id_5d383234_fk_accounts_user_id` FOREIGN KEY (`processed_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `accounts_report_reporter_id_3d4247eb_fk_accounts_user_id` FOREIGN KEY (`reporter_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `accounts_report_chk_1` CHECK ((`target_id` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `accounts_user`
DROP TABLE IF EXISTS `accounts_user`;
CREATE TABLE `accounts_user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  `email` varchar(254) NOT NULL,
  `activity_name` varchar(150) NOT NULL,
  `auth_provider` varchar(20) DEFAULT NULL,
  `band_creation_blocked_until` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `accounts_user_groups`
DROP TABLE IF EXISTS `accounts_user_groups`;
CREATE TABLE `accounts_user_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `accounts_user_groups_user_id_group_id_59c0b32f_uniq` (`user_id`,`group_id`),
  KEY `accounts_user_groups_group_id_bd11a704_fk_auth_group_id` (`group_id`),
  CONSTRAINT `accounts_user_groups_group_id_bd11a704_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `accounts_user_groups_user_id_52b62117_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `accounts_user_user_permissions`
DROP TABLE IF EXISTS `accounts_user_user_permissions`;
CREATE TABLE `accounts_user_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `accounts_user_user_permi_user_id_permission_id_2ab516c2_uniq` (`user_id`,`permission_id`),
  KEY `accounts_user_user_p_permission_id_113bb443_fk_auth_perm` (`permission_id`),
  CONSTRAINT `accounts_user_user_p_permission_id_113bb443_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `accounts_user_user_p_user_id_e4f0a161_fk_accounts_` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `accounts_userblock`
DROP TABLE IF EXISTS `accounts_userblock`;
CREATE TABLE `accounts_userblock` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `blocked_id` bigint NOT NULL,
  `blocker_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `accounts_userblock_blocker_id_blocked_id_52bc3bdd_uniq` (`blocker_id`,`blocked_id`),
  KEY `accounts_us_blocker_47e452_idx` (`blocker_id`),
  KEY `accounts_us_blocked_8e644c_idx` (`blocked_id`),
  CONSTRAINT `accounts_userblock_blocked_id_85be0646_fk_accounts_user_id` FOREIGN KEY (`blocked_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `accounts_userblock_blocker_id_cad7f1f0_fk_accounts_user_id` FOREIGN KEY (`blocker_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `accounts_userprofile`
DROP TABLE IF EXISTS `accounts_userprofile`;
CREATE TABLE `accounts_userprofile` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `profile_image` varchar(100) DEFAULT NULL,
  `name` varchar(100) NOT NULL,
  `gender` varchar(10) NOT NULL,
  `age_range` varchar(50) NOT NULL,
  `birthday` date DEFAULT NULL,
  `birth_year` int unsigned DEFAULT NULL,
  `phone_number` varchar(20) NOT NULL,
  `shipping_receiver` varchar(100) NOT NULL,
  `shipping_phone_number` varchar(20) NOT NULL,
  `shipping_address` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `accounts_userprofile_user_id_92240672_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `accounts_userprofile_chk_1` CHECK ((`birth_year` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `auth_group`
DROP TABLE IF EXISTS `auth_group`;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `auth_group_permissions`
DROP TABLE IF EXISTS `auth_group_permissions`;
CREATE TABLE `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `auth_permission`
DROP TABLE IF EXISTS `auth_permission`;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=149 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `badmintok_badmintokbanner`
DROP TABLE IF EXISTS `badmintok_badmintokbanner`;
CREATE TABLE `badmintok_badmintokbanner` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(100) NOT NULL,
  `image` varchar(100) NOT NULL,
  `link_url` varchar(200) NOT NULL,
  `alt_text` varchar(255) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `display_order` int unsigned NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `badmintok_badmintokbanner_chk_1` CHECK ((`display_order` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `badmintok_notice`
DROP TABLE IF EXISTS `badmintok_notice`;
CREATE TABLE `badmintok_notice` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `content` longtext NOT NULL,
  `is_pinned` tinyint(1) NOT NULL,
  `view_count` int unsigned NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `author_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `badmintok_n_is_pinn_5166ff_idx` (`is_pinned` DESC,`created_at` DESC),
  KEY `badmintok_n_author__fb9a7f_idx` (`author_id`),
  CONSTRAINT `badmintok_notice_author_id_e0d92273_fk_accounts_user_id` FOREIGN KEY (`author_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `badmintok_notice_chk_1` CHECK ((`view_count` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `band_band`
DROP TABLE IF EXISTS `band_band`;
CREATE TABLE `band_band` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `description` varchar(500) NOT NULL,
  `cover_image` varchar(100) DEFAULT NULL,
  `profile_image` varchar(100) DEFAULT NULL,
  `is_public` tinyint(1) NOT NULL,
  `join_approval_required` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `created_by_id` bigint NOT NULL,
  `band_type` varchar(20) NOT NULL,
  `region` varchar(20) NOT NULL,
  `flash_region_detail` varchar(20) NOT NULL,
  `categories` varchar(100) NOT NULL,
  `approved_at` datetime(6) DEFAULT NULL,
  `approved_by_id` bigint DEFAULT NULL,
  `is_approved` tinyint(1) NOT NULL,
  `rejection_reason` longtext NOT NULL,
  `detailed_description` longtext NOT NULL,
  `deletion_approved_at` datetime(6) DEFAULT NULL,
  `deletion_approved_by_id` bigint DEFAULT NULL,
  `deletion_reason` longtext NOT NULL,
  `deletion_requested` tinyint(1) NOT NULL,
  `deletion_requested_at` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `band_band_created_345cac_idx` (`created_by_id`),
  KEY `band_band_is_publ_5238f0_idx` (`is_public`),
  KEY `band_band_approved_by_id_3e3ae1a5_fk_accounts_user_id` (`approved_by_id`),
  KEY `band_band_deletion_approved_by_id_1f5e3b67_fk_accounts_user_id` (`deletion_approved_by_id`),
  CONSTRAINT `band_band_approved_by_id_3e3ae1a5_fk_accounts_user_id` FOREIGN KEY (`approved_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `band_band_created_by_id_1e3821b4_fk_accounts_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `band_band_deletion_approved_by_id_1f5e3b67_fk_accounts_user_id` FOREIGN KEY (`deletion_approved_by_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `band_bandcomment`
DROP TABLE IF EXISTS `band_bandcomment`;
CREATE TABLE `band_bandcomment` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `content` longtext NOT NULL,
  `like_count` int NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `author_id` bigint NOT NULL,
  `parent_id` bigint DEFAULT NULL,
  `post_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `band_bandco_post_id_c4e0b5_idx` (`post_id`),
  KEY `band_bandco_author__5bbe03_idx` (`author_id`),
  KEY `band_bandco_parent__f605f1_idx` (`parent_id`),
  KEY `band_bandco_created_07143a_idx` (`created_at` DESC),
  CONSTRAINT `band_bandcomment_author_id_8c65343b_fk_accounts_user_id` FOREIGN KEY (`author_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `band_bandcomment_parent_id_d73677e6_fk_band_bandcomment_id` FOREIGN KEY (`parent_id`) REFERENCES `band_bandcomment` (`id`),
  CONSTRAINT `band_bandcomment_post_id_e5ff98ca_fk_band_bandpost_id` FOREIGN KEY (`post_id`) REFERENCES `band_bandpost` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `band_bandcommentlike`
DROP TABLE IF EXISTS `band_bandcommentlike`;
CREATE TABLE `band_bandcommentlike` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `comment_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `band_bandcommentlike_comment_id_user_id_4435d9aa_uniq` (`comment_id`,`user_id`),
  KEY `band_bandco_comment_1dd4eb_idx` (`comment_id`),
  KEY `band_bandco_user_id_90e30e_idx` (`user_id`),
  CONSTRAINT `band_bandcommentlike_comment_id_dbb078ba_fk_band_bandcomment_id` FOREIGN KEY (`comment_id`) REFERENCES `band_bandcomment` (`id`),
  CONSTRAINT `band_bandcommentlike_user_id_344d06ce_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `band_bandmember`
DROP TABLE IF EXISTS `band_bandmember`;
CREATE TABLE `band_bandmember` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `role` varchar(20) NOT NULL,
  `status` varchar(20) NOT NULL,
  `joined_at` datetime(6) NOT NULL,
  `last_visited_at` datetime(6) NOT NULL,
  `band_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `band_bandmember_band_id_user_id_00b67f08_uniq` (`band_id`,`user_id`),
  KEY `band_bandme_band_id_6f3a09_idx` (`band_id`),
  KEY `band_bandme_user_id_38f4db_idx` (`user_id`),
  KEY `band_bandme_role_c2881f_idx` (`role`),
  KEY `band_bandme_status_2b8d7b_idx` (`status`),
  CONSTRAINT `band_bandmember_band_id_b0c50438_fk_band_band_id` FOREIGN KEY (`band_id`) REFERENCES `band_band` (`id`),
  CONSTRAINT `band_bandmember_user_id_d58c293a_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `band_bandpost`
DROP TABLE IF EXISTS `band_bandpost`;
CREATE TABLE `band_bandpost` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `content` longtext NOT NULL,
  `post_type` varchar(20) NOT NULL,
  `is_pinned` tinyint(1) NOT NULL,
  `is_notice` tinyint(1) NOT NULL,
  `view_count` int NOT NULL,
  `like_count` int NOT NULL,
  `comment_count` int NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `author_id` bigint NOT NULL,
  `band_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `band_bandpo_band_id_d82544_idx` (`band_id`),
  KEY `band_bandpo_author__4f2153_idx` (`author_id`),
  KEY `band_bandpo_post_ty_2a124c_idx` (`post_type`),
  KEY `band_bandpo_is_pinn_ee14ff_idx` (`is_pinned`),
  KEY `band_bandpo_created_7a1213_idx` (`created_at` DESC),
  CONSTRAINT `band_bandpost_author_id_cbf93e3e_fk_accounts_user_id` FOREIGN KEY (`author_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `band_bandpost_band_id_173bbce3_fk_band_band_id` FOREIGN KEY (`band_id`) REFERENCES `band_band` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `band_bandpostimage`
DROP TABLE IF EXISTS `band_bandpostimage`;
CREATE TABLE `band_bandpostimage` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `image` varchar(100) NOT NULL,
  `order_index` int NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `post_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `band_bandpo_post_id_de2477_idx` (`post_id`),
  KEY `band_bandpo_post_id_a758b8_idx` (`post_id`,`order_index`),
  CONSTRAINT `band_bandpostimage_post_id_84274863_fk_band_bandpost_id` FOREIGN KEY (`post_id`) REFERENCES `band_bandpost` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `band_bandpostlike`
DROP TABLE IF EXISTS `band_bandpostlike`;
CREATE TABLE `band_bandpostlike` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `post_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `band_bandpostlike_post_id_user_id_6032444f_uniq` (`post_id`,`user_id`),
  KEY `band_bandpo_post_id_28de87_idx` (`post_id`),
  KEY `band_bandpo_user_id_2340a7_idx` (`user_id`),
  CONSTRAINT `band_bandpostlike_post_id_331e89b3_fk_band_bandpost_id` FOREIGN KEY (`post_id`) REFERENCES `band_bandpost` (`id`),
  CONSTRAINT `band_bandpostlike_user_id_6449feed_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `band_bandschedule`
DROP TABLE IF EXISTS `band_bandschedule`;
CREATE TABLE `band_bandschedule` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `description` longtext NOT NULL,
  `start_datetime` datetime(6) NOT NULL,
  `end_datetime` datetime(6) DEFAULT NULL,
  `location` varchar(200) NOT NULL,
  `max_participants` int DEFAULT NULL,
  `current_participants` int NOT NULL,
  `requires_approval` tinyint(1) NOT NULL,
  `application_deadline` datetime(6) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `band_id` bigint NOT NULL,
  `created_by_id` bigint NOT NULL,
  `post_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `band_bandsc_band_id_e8d32a_idx` (`band_id`),
  KEY `band_bandsc_post_id_ef3715_idx` (`post_id`),
  KEY `band_bandsc_start_d_a0274e_idx` (`start_datetime`),
  KEY `band_bandsc_created_d7569b_idx` (`created_by_id`),
  KEY `band_bandsc_applica_928ad6_idx` (`application_deadline`),
  CONSTRAINT `band_bandschedule_band_id_e9849d1d_fk_band_band_id` FOREIGN KEY (`band_id`) REFERENCES `band_band` (`id`),
  CONSTRAINT `band_bandschedule_created_by_id_e1b5d87d_fk_accounts_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `band_bandschedule_post_id_c65c8b1d_fk_band_bandpost_id` FOREIGN KEY (`post_id`) REFERENCES `band_bandpost` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `band_bandscheduleapplication`
DROP TABLE IF EXISTS `band_bandscheduleapplication`;
CREATE TABLE `band_bandscheduleapplication` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `status` varchar(20) NOT NULL,
  `applied_at` datetime(6) NOT NULL,
  `reviewed_at` datetime(6) DEFAULT NULL,
  `rejection_reason` longtext NOT NULL,
  `notes` longtext NOT NULL,
  `reviewed_by_id` bigint DEFAULT NULL,
  `schedule_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `band_bandscheduleapplication_schedule_id_user_id_b810600d_uniq` (`schedule_id`,`user_id`),
  KEY `band_bandsc_schedul_66c378_idx` (`schedule_id`),
  KEY `band_bandsc_user_id_32fd78_idx` (`user_id`),
  KEY `band_bandsc_status_0630b8_idx` (`status`),
  KEY `band_bandsc_applied_e76bde_idx` (`applied_at` DESC),
  KEY `band_bandsc_reviewe_e7af79_idx` (`reviewed_by_id`),
  CONSTRAINT `band_bandscheduleapp_reviewed_by_id_ab985f92_fk_accounts_` FOREIGN KEY (`reviewed_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `band_bandscheduleapp_schedule_id_a2ed5663_fk_band_band` FOREIGN KEY (`schedule_id`) REFERENCES `band_bandschedule` (`id`),
  CONSTRAINT `band_bandscheduleapp_user_id_734a6359_fk_accounts_` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `band_bandscheduleimage`
DROP TABLE IF EXISTS `band_bandscheduleimage`;
CREATE TABLE `band_bandscheduleimage` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `image` varchar(100) NOT NULL,
  `order` int NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `schedule_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `band_bandsc_schedul_3b0667_idx` (`schedule_id`,`order`),
  CONSTRAINT `band_bandscheduleima_schedule_id_92f4e110_fk_band_band` FOREIGN KEY (`schedule_id`) REFERENCES `band_bandschedule` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `band_bandvote`
DROP TABLE IF EXISTS `band_bandvote`;
CREATE TABLE `band_bandvote` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `is_multiple_choice` tinyint(1) NOT NULL,
  `end_datetime` datetime(6) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `post_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `post_id` (`post_id`),
  KEY `band_bandvo_post_id_bc07d7_idx` (`post_id`),
  KEY `band_bandvo_end_dat_30d1a2_idx` (`end_datetime`),
  CONSTRAINT `band_bandvote_post_id_32bc7e5a_fk_band_bandpost_id` FOREIGN KEY (`post_id`) REFERENCES `band_bandpost` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `band_bandvotechoice`
DROP TABLE IF EXISTS `band_bandvotechoice`;
CREATE TABLE `band_bandvotechoice` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `user_id` bigint NOT NULL,
  `vote_id` bigint NOT NULL,
  `option_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `band_bandvotechoice_vote_id_user_id_option_id_2aa8be43_uniq` (`vote_id`,`user_id`,`option_id`),
  KEY `band_bandvo_vote_id_0531e3_idx` (`vote_id`),
  KEY `band_bandvo_option__85e2f5_idx` (`option_id`),
  KEY `band_bandvo_user_id_aa28d5_idx` (`user_id`),
  CONSTRAINT `band_bandvotechoice_option_id_86383e78_fk_band_bandvoteoption_id` FOREIGN KEY (`option_id`) REFERENCES `band_bandvoteoption` (`id`),
  CONSTRAINT `band_bandvotechoice_user_id_a7b911f6_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `band_bandvotechoice_vote_id_e1947256_fk_band_bandvote_id` FOREIGN KEY (`vote_id`) REFERENCES `band_bandvote` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `band_bandvoteoption`
DROP TABLE IF EXISTS `band_bandvoteoption`;
CREATE TABLE `band_bandvoteoption` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `option_text` varchar(200) NOT NULL,
  `vote_count` int NOT NULL,
  `order_index` int NOT NULL,
  `vote_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `band_bandvo_vote_id_9937d3_idx` (`vote_id`),
  KEY `band_bandvo_vote_id_0d90e6_idx` (`vote_id`,`order_index`),
  CONSTRAINT `band_bandvoteoption_vote_id_2af6388e_fk_band_bandvote_id` FOREIGN KEY (`vote_id`) REFERENCES `band_bandvote` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `community_category`
DROP TABLE IF EXISTS `community_category`;
CREATE TABLE `community_category` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `slug` varchar(50) NOT NULL,
  `display_order` int unsigned NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `parent_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `slug` (`slug`),
  KEY `community_c_slug_777ae5_idx` (`slug`),
  KEY `community_c_is_acti_5c99dc_idx` (`is_active`,`display_order`),
  KEY `community_c_parent__eb9340_idx` (`parent_id`),
  CONSTRAINT `community_category_parent_id_f769c6e3_fk_community_category_id` FOREIGN KEY (`parent_id`) REFERENCES `community_category` (`id`),
  CONSTRAINT `community_category_chk_1` CHECK ((`display_order` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `community_comment`
DROP TABLE IF EXISTS `community_comment`;
CREATE TABLE `community_comment` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `content` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `like_count` int unsigned NOT NULL,
  `is_deleted` tinyint(1) NOT NULL,
  `author_id` bigint NOT NULL,
  `parent_id` bigint DEFAULT NULL,
  `post_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `community_c_post_id_bea033_idx` (`post_id`,`created_at`),
  KEY `community_c_author__1e6995_idx` (`author_id`),
  KEY `community_c_parent__5a3862_idx` (`parent_id`),
  CONSTRAINT `community_comment_author_id_51c65c2a_fk_accounts_user_id` FOREIGN KEY (`author_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `community_comment_parent_id_2fd9f894_fk_community_comment_id` FOREIGN KEY (`parent_id`) REFERENCES `community_comment` (`id`),
  CONSTRAINT `community_comment_post_id_12b521a8_fk_community_post_id` FOREIGN KEY (`post_id`) REFERENCES `community_post` (`id`),
  CONSTRAINT `community_comment_chk_1` CHECK ((`like_count` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `community_comment_likes`
DROP TABLE IF EXISTS `community_comment_likes`;
CREATE TABLE `community_comment_likes` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `comment_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `community_comment_likes_comment_id_user_id_ddb824a0_uniq` (`comment_id`,`user_id`),
  KEY `community_comment_likes_user_id_3d69d764_fk_accounts_user_id` (`user_id`),
  CONSTRAINT `community_comment_li_comment_id_3ec95328_fk_community` FOREIGN KEY (`comment_id`) REFERENCES `community_comment` (`id`),
  CONSTRAINT `community_comment_likes_user_id_3d69d764_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `community_post`
DROP TABLE IF EXISTS `community_post`;
CREATE TABLE `community_post` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `category_id` int DEFAULT NULL,
  `content` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `view_count` int unsigned NOT NULL,
  `like_count` int unsigned NOT NULL,
  `comment_count` int unsigned NOT NULL,
  `is_deleted` tinyint(1) NOT NULL,
  `is_pinned` tinyint(1) NOT NULL,
  `author_id` bigint NOT NULL,
  `source` varchar(20) NOT NULL,
  `published_at` datetime(6) DEFAULT NULL,
  `slug` varchar(45) NOT NULL,
  `thumbnail` varchar(100) DEFAULT NULL,
  `focus_keyword` varchar(100) NOT NULL,
  `is_draft` tinyint(1) NOT NULL,
  `meta_description` longtext NOT NULL,
  `thumbnail_alt` varchar(200) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `community_p_created_6febb2_idx` (`created_at` DESC),
  KEY `community_p_author__5261da_idx` (`author_id`),
  KEY `community_p_source_ece6fc_idx` (`source`,`created_at` DESC),
  KEY `community_p_slug_614d88_idx` (`slug`),
  KEY `community_p_publish_9a7d6d_idx` (`published_at`),
  KEY `community_post_slug_1c7322e5` (`slug`),
  CONSTRAINT `community_post_author_id_a6c5f564_fk_accounts_user_id` FOREIGN KEY (`author_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `community_post_chk_1` CHECK ((`view_count` >= 0)),
  CONSTRAINT `community_post_chk_2` CHECK ((`like_count` >= 0)),
  CONSTRAINT `community_post_chk_3` CHECK ((`comment_count` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `community_post_likes`
DROP TABLE IF EXISTS `community_post_likes`;
CREATE TABLE `community_post_likes` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `post_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `community_post_likes_post_id_user_id_7155e6ea_uniq` (`post_id`,`user_id`),
  KEY `community_post_likes_user_id_88523dbc_fk_accounts_user_id` (`user_id`),
  CONSTRAINT `community_post_likes_post_id_3dbbbf10_fk_community_post_id` FOREIGN KEY (`post_id`) REFERENCES `community_post` (`id`),
  CONSTRAINT `community_post_likes_user_id_88523dbc_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `community_postimage`
DROP TABLE IF EXISTS `community_postimage`;
CREATE TABLE `community_postimage` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `image` varchar(100) NOT NULL,
  `order` int unsigned NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `post_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `community_p_post_id_b89cc2_idx` (`post_id`,`order`),
  CONSTRAINT `community_postimage_post_id_bb183c06_fk_community_post_id` FOREIGN KEY (`post_id`) REFERENCES `community_post` (`id`),
  CONSTRAINT `community_postimage_chk_1` CHECK ((`order` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `community_postshare`
DROP TABLE IF EXISTS `community_postshare`;
CREATE TABLE `community_postshare` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `shared_at` datetime(6) NOT NULL,
  `post_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `community_postshare_post_id_user_id_0aa98512_uniq` (`post_id`,`user_id`),
  KEY `community_p_post_id_1686b9_idx` (`post_id`),
  KEY `community_p_user_id_f8f7f7_idx` (`user_id`),
  CONSTRAINT `community_postshare_post_id_085b84c5_fk_community_post_id` FOREIGN KEY (`post_id`) REFERENCES `community_post` (`id`),
  CONSTRAINT `community_postshare_user_id_1cad0464_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `contests_contest`
DROP TABLE IF EXISTS `contests_contest`;
CREATE TABLE `contests_contest` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `slug` varchar(45) NOT NULL,
  `image` varchar(100) DEFAULT NULL,
  `schedule_start` date NOT NULL,
  `schedule_end` date DEFAULT NULL,
  `event_division` varchar(255) NOT NULL,
  `registration_start` date NOT NULL,
  `registration_end` date NOT NULL,
  `entry_fee` varchar(100) NOT NULL,
  `competition_type` varchar(100) NOT NULL,
  `participant_reward` varchar(255) NOT NULL,
  `sponsor_id` bigint NOT NULL,
  `award_reward` json DEFAULT NULL,
  `registration_link` varchar(200) NOT NULL,
  `description` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `category_id` bigint DEFAULT NULL,
  `is_qualifying` tinyint(1) NOT NULL,
  `registration_name` varchar(200) NOT NULL,
  `award_reward_text` longtext NOT NULL,
  `participant_target` longtext NOT NULL,
  `region` varchar(20) NOT NULL,
  `region_detail` varchar(200) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug` (`slug`),
  KEY `contests_contest_category_id_8d9e930e_fk_contests_` (`category_id`),
  CONSTRAINT `contests_contest_category_id_8d9e930e_fk_contests_` FOREIGN KEY (`category_id`) REFERENCES `contests_contestcategory` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `contests_contest_likes`
DROP TABLE IF EXISTS `contests_contest_likes`;
CREATE TABLE `contests_contest_likes` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `contest_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `contests_contest_likes_contest_id_user_id_7a351abe_uniq` (`contest_id`,`user_id`),
  KEY `contests_contest_likes_user_id_95523924_fk_accounts_user_id` (`user_id`),
  CONSTRAINT `contests_contest_lik_contest_id_68b60daf_fk_contests_` FOREIGN KEY (`contest_id`) REFERENCES `contests_contest` (`id`),
  CONSTRAINT `contests_contest_likes_user_id_95523924_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `contests_contestcategory`
DROP TABLE IF EXISTS `contests_contestcategory`;
CREATE TABLE `contests_contestcategory` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `color` varchar(7) NOT NULL,
  `description` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `contests_contestimage`
DROP TABLE IF EXISTS `contests_contestimage`;
CREATE TABLE `contests_contestimage` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `image` varchar(100) NOT NULL,
  `order` int unsigned NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `contest_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `contests_contestimage_contest_id_3567341b_fk_contests_contest_id` (`contest_id`),
  CONSTRAINT `contests_contestimage_contest_id_3567341b_fk_contests_contest_id` FOREIGN KEY (`contest_id`) REFERENCES `contests_contest` (`id`),
  CONSTRAINT `contests_contestimage_chk_1` CHECK ((`order` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `contests_contestschedule`
DROP TABLE IF EXISTS `contests_contestschedule`;
CREATE TABLE `contests_contestschedule` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `date` date NOT NULL,
  `events` json DEFAULT NULL,
  `ages` json DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `contest_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `contests_contestsche_contest_id_de6931dd_fk_contests_` (`contest_id`),
  CONSTRAINT `contests_contestsche_contest_id_de6931dd_fk_contests_` FOREIGN KEY (`contest_id`) REFERENCES `contests_contest` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `contests_sponsor`
DROP TABLE IF EXISTS `contests_sponsor`;
CREATE TABLE `contests_sponsor` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `django_admin_log`
DROP TABLE IF EXISTS `django_admin_log`;
CREATE TABLE `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_accounts_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `django_content_type`
DROP TABLE IF EXISTS `django_content_type`;
CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `django_migrations`
DROP TABLE IF EXISTS `django_migrations`;
CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=79 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table structure for table `django_session`
DROP TABLE IF EXISTS `django_session`;
CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS=1;
