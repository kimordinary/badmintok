
-- Migration: accounts.0001_initial
--
-- Create model User
--
CREATE TABLE `accounts_user` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `password` varchar(128) NOT NULL, `last_login` datetime(6) NULL, `is_superuser` bool NOT NULL, `first_name` varchar(150) NOT NULL, `last_name` varchar(150) NOT NULL, `is_staff` bool NOT NULL, `is_active` bool NOT NULL, `date_joined` datetime(6) NOT NULL, `email` varchar(254) NOT NULL UNIQUE, `activity_name` varchar(150) NOT NULL);
CREATE TABLE `accounts_user_groups` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `user_id` bigint NOT NULL, `group_id` integer NOT NULL);
CREATE TABLE `accounts_user_user_permissions` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `user_id` bigint NOT NULL, `permission_id` integer NOT NULL);
ALTER TABLE `accounts_user_groups` ADD CONSTRAINT `accounts_user_groups_user_id_group_id_59c0b32f_uniq` UNIQUE (`user_id`, `group_id`);
ALTER TABLE `accounts_user_groups` ADD CONSTRAINT `accounts_user_groups_user_id_52b62117_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`);
ALTER TABLE `accounts_user_groups` ADD CONSTRAINT `accounts_user_groups_group_id_bd11a704_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`);
ALTER TABLE `accounts_user_user_permissions` ADD CONSTRAINT `accounts_user_user_permi_user_id_permission_id_2ab516c2_uniq` UNIQUE (`user_id`, `permission_id`);
ALTER TABLE `accounts_user_user_permissions` ADD CONSTRAINT `accounts_user_user_p_user_id_e4f0a161_fk_accounts_` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`);
ALTER TABLE `accounts_user_user_permissions` ADD CONSTRAINT `accounts_user_user_p_permission_id_113bb443_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`);


-- Migration: accounts.0002_userprofile
--
-- Create model UserProfile
--
CREATE TABLE `accounts_userprofile` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `profile_image` varchar(100) NULL, `name` varchar(100) NOT NULL, `gender` varchar(10) NOT NULL, `age_range` varchar(50) NOT NULL, `birthday` date NULL, `birth_year` integer UNSIGNED NULL CHECK (`birth_year` >= 0), `phone_number` varchar(20) NOT NULL, `shipping_receiver` varchar(100) NOT NULL, `shipping_phone_number` varchar(20) NOT NULL, `shipping_address` longtext NOT NULL, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `user_id` bigint NOT NULL UNIQUE);
ALTER TABLE `accounts_userprofile` ADD CONSTRAINT `accounts_userprofile_user_id_92240672_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`);


-- Migration: accounts.0003_alter_userprofile_profile_image
--
-- Alter field profile_image on userprofile
--
-- (no-op)


-- Migration: accounts.0004_user_auth_provider
--
-- Add field auth_provider to user
--
ALTER TABLE `accounts_user` ADD COLUMN `auth_provider` varchar(20) NULL;


-- Migration: accounts.0005_user_band_creation_blocked_until
--
-- Add field band_creation_blocked_until to user
--
ALTER TABLE `accounts_user` ADD COLUMN `band_creation_blocked_until` datetime(6) NULL;


-- Migration: accounts.0006_inquiry_report_userblock
--
-- Create model Inquiry
--
CREATE TABLE `accounts_inquiry` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `category` varchar(20) NOT NULL, `title` varchar(200) NOT NULL, `content` longtext NOT NULL, `status` varchar(20) NOT NULL, `admin_response` longtext NOT NULL, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `answered_at` datetime(6) NULL, `answered_by_id` bigint NULL, `user_id` bigint NOT NULL);
--
-- Create model Report
--
CREATE TABLE `accounts_report` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `report_type` varchar(20) NOT NULL, `target_id` integer UNSIGNED NOT NULL CHECK (`target_id` >= 0), `reason` longtext NOT NULL, `status` varchar(20) NOT NULL, `admin_note` longtext NOT NULL, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `processed_at` datetime(6) NULL, `processed_by_id` bigint NULL, `reporter_id` bigint NOT NULL);
--
-- Create model UserBlock
--
CREATE TABLE `accounts_userblock` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `created_at` datetime(6) NOT NULL, `blocked_id` bigint NOT NULL, `blocker_id` bigint NOT NULL);
ALTER TABLE `accounts_inquiry` ADD CONSTRAINT `accounts_inquiry_answered_by_id_48f64c10_fk_accounts_user_id` FOREIGN KEY (`answered_by_id`) REFERENCES `accounts_user` (`id`);
ALTER TABLE `accounts_inquiry` ADD CONSTRAINT `accounts_inquiry_user_id_aff3d7e4_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`);
CREATE INDEX `accounts_in_user_id_ba6a9d_idx` ON `accounts_inquiry` (`user_id`);
CREATE INDEX `accounts_in_status_b3a7cf_idx` ON `accounts_inquiry` (`status`);
CREATE INDEX `accounts_in_created_fa689f_idx` ON `accounts_inquiry` (`created_at` DESC);
ALTER TABLE `accounts_report` ADD CONSTRAINT `accounts_report_processed_by_id_5d383234_fk_accounts_user_id` FOREIGN KEY (`processed_by_id`) REFERENCES `accounts_user` (`id`);
ALTER TABLE `accounts_report` ADD CONSTRAINT `accounts_report_reporter_id_3d4247eb_fk_accounts_user_id` FOREIGN KEY (`reporter_id`) REFERENCES `accounts_user` (`id`);
CREATE INDEX `accounts_re_reporte_8da0cd_idx` ON `accounts_report` (`reporter_id`);
CREATE INDEX `accounts_re_report__eda831_idx` ON `accounts_report` (`report_type`, `target_id`);
CREATE INDEX `accounts_re_status_859365_idx` ON `accounts_report` (`status`);
CREATE INDEX `accounts_re_created_08a081_idx` ON `accounts_report` (`created_at` DESC);
ALTER TABLE `accounts_userblock` ADD CONSTRAINT `accounts_userblock_blocker_id_blocked_id_52bc3bdd_uniq` UNIQUE (`blocker_id`, `blocked_id`);
ALTER TABLE `accounts_userblock` ADD CONSTRAINT `accounts_userblock_blocked_id_85be0646_fk_accounts_user_id` FOREIGN KEY (`blocked_id`) REFERENCES `accounts_user` (`id`);
ALTER TABLE `accounts_userblock` ADD CONSTRAINT `accounts_userblock_blocker_id_cad7f1f0_fk_accounts_user_id` FOREIGN KEY (`blocker_id`) REFERENCES `accounts_user` (`id`);
CREATE INDEX `accounts_us_blocker_47e452_idx` ON `accounts_userblock` (`blocker_id`);
CREATE INDEX `accounts_us_blocked_8e644c_idx` ON `accounts_userblock` (`blocked_id`);


-- Migration: band.0001_initial
--
-- Create model Band
--
CREATE TABLE `band_band` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `name` varchar(200) NOT NULL, `description` longtext NOT NULL, `cover_image` varchar(100) NULL, `profile_image` varchar(100) NULL, `is_public` bool NOT NULL, `join_approval_required` bool NOT NULL, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `created_by_id` bigint NOT NULL);
--
-- Create model BandComment
--
CREATE TABLE `band_bandcomment` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `content` longtext NOT NULL, `like_count` integer NOT NULL, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `author_id` bigint NOT NULL, `parent_id` bigint NULL);
--
-- Create model BandCommentLike
--
CREATE TABLE `band_bandcommentlike` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `created_at` datetime(6) NOT NULL, `comment_id` bigint NOT NULL, `user_id` bigint NOT NULL);
--
-- Create model BandMember
--
CREATE TABLE `band_bandmember` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `role` varchar(20) NOT NULL, `status` varchar(20) NOT NULL, `joined_at` datetime(6) NOT NULL, `last_visited_at` datetime(6) NOT NULL, `band_id` bigint NOT NULL, `user_id` bigint NOT NULL);
--
-- Create model BandPost
--
CREATE TABLE `band_bandpost` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `title` varchar(200) NOT NULL, `content` longtext NOT NULL, `post_type` varchar(20) NOT NULL, `is_pinned` bool NOT NULL, `is_notice` bool NOT NULL, `view_count` integer NOT NULL, `like_count` integer NOT NULL, `comment_count` integer NOT NULL, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `author_id` bigint NOT NULL, `band_id` bigint NOT NULL);
--
-- Add field post to bandcomment
--
ALTER TABLE `band_bandcomment` ADD COLUMN `post_id` bigint NOT NULL , ADD CONSTRAINT `band_bandcomment_post_id_e5ff98ca_fk_band_bandpost_id` FOREIGN KEY (`post_id`) REFERENCES `band_bandpost`(`id`);
--
-- Create model BandPostImage
--
CREATE TABLE `band_bandpostimage` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `image` varchar(100) NOT NULL, `order_index` integer NOT NULL, `created_at` datetime(6) NOT NULL, `post_id` bigint NOT NULL);
--
-- Create model BandPostLike
--
CREATE TABLE `band_bandpostlike` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `created_at` datetime(6) NOT NULL, `post_id` bigint NOT NULL, `user_id` bigint NOT NULL);
--
-- Create model BandSchedule
--
CREATE TABLE `band_bandschedule` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `title` varchar(200) NOT NULL, `description` longtext NOT NULL, `start_datetime` datetime(6) NOT NULL, `end_datetime` datetime(6) NULL, `location` varchar(200) NOT NULL, `max_participants` integer NULL, `current_participants` integer NOT NULL, `requires_approval` bool NOT NULL, `application_deadline` datetime(6) NULL, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `band_id` bigint NOT NULL, `created_by_id` bigint NOT NULL, `post_id` bigint NULL);
--
-- Create model BandScheduleApplication
--
CREATE TABLE `band_bandscheduleapplication` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `status` varchar(20) NOT NULL, `applied_at` datetime(6) NOT NULL, `reviewed_at` datetime(6) NULL, `rejection_reason` longtext NOT NULL, `notes` longtext NOT NULL, `reviewed_by_id` bigint NULL, `schedule_id` bigint NOT NULL, `user_id` bigint NOT NULL);
--
-- Create model BandVote
--
CREATE TABLE `band_bandvote` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `title` varchar(200) NOT NULL, `is_multiple_choice` bool NOT NULL, `end_datetime` datetime(6) NULL, `created_at` datetime(6) NOT NULL, `post_id` bigint NOT NULL UNIQUE);
--
-- Create model BandVoteOption
--
CREATE TABLE `band_bandvoteoption` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `option_text` varchar(200) NOT NULL, `vote_count` integer NOT NULL, `order_index` integer NOT NULL, `vote_id` bigint NOT NULL);
--
-- Create model BandVoteChoice
--
CREATE TABLE `band_bandvotechoice` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `created_at` datetime(6) NOT NULL, `user_id` bigint NOT NULL, `vote_id` bigint NOT NULL, `option_id` bigint NOT NULL);
--
-- Create index band_band_created_345cac_idx on field(s) created_by of model band
--
CREATE INDEX `band_band_created_345cac_idx` ON `band_band` (`created_by_id`);
--
-- Create index band_band_is_publ_5238f0_idx on field(s) is_public of model band
--
CREATE INDEX `band_band_is_publ_5238f0_idx` ON `band_band` (`is_public`);
--
-- Create index band_bandco_comment_1dd4eb_idx on field(s) comment of model bandcommentlike
--
CREATE INDEX `band_bandco_comment_1dd4eb_idx` ON `band_bandcommentlike` (`comment_id`);
--
-- Create index band_bandco_user_id_90e30e_idx on field(s) user of model bandcommentlike
--
CREATE INDEX `band_bandco_user_id_90e30e_idx` ON `band_bandcommentlike` (`user_id`);
--
-- Alter unique_together for bandcommentlike (1 constraint(s))
--
ALTER TABLE `band_bandcommentlike` ADD CONSTRAINT `band_bandcommentlike_comment_id_user_id_4435d9aa_uniq` UNIQUE (`comment_id`, `user_id`);
--
-- Create index band_bandme_band_id_6f3a09_idx on field(s) band of model bandmember
--
CREATE INDEX `band_bandme_band_id_6f3a09_idx` ON `band_bandmember` (`band_id`);
--
-- Create index band_bandme_user_id_38f4db_idx on field(s) user of model bandmember
--
CREATE INDEX `band_bandme_user_id_38f4db_idx` ON `band_bandmember` (`user_id`);
--
-- Create index band_bandme_role_c2881f_idx on field(s) role of model bandmember
--
CREATE INDEX `band_bandme_role_c2881f_idx` ON `band_bandmember` (`role`);
--
-- Create index band_bandme_status_2b8d7b_idx on field(s) status of model bandmember
--
CREATE INDEX `band_bandme_status_2b8d7b_idx` ON `band_bandmember` (`status`);
--
-- Alter unique_together for bandmember (1 constraint(s))
--
ALTER TABLE `band_bandmember` ADD CONSTRAINT `band_bandmember_band_id_user_id_00b67f08_uniq` UNIQUE (`band_id`, `user_id`);
--
-- Create index band_bandpo_band_id_d82544_idx on field(s) band of model bandpost
--
CREATE INDEX `band_bandpo_band_id_d82544_idx` ON `band_bandpost` (`band_id`);
--
-- Create index band_bandpo_author__4f2153_idx on field(s) author of model bandpost
--
CREATE INDEX `band_bandpo_author__4f2153_idx` ON `band_bandpost` (`author_id`);
--
-- Create index band_bandpo_post_ty_2a124c_idx on field(s) post_type of model bandpost
--
CREATE INDEX `band_bandpo_post_ty_2a124c_idx` ON `band_bandpost` (`post_type`);
--
-- Create index band_bandpo_is_pinn_ee14ff_idx on field(s) is_pinned of model bandpost
--
CREATE INDEX `band_bandpo_is_pinn_ee14ff_idx` ON `band_bandpost` (`is_pinned`);
--
-- Create index band_bandpo_created_7a1213_idx on field(s) -created_at of model bandpost
--
CREATE INDEX `band_bandpo_created_7a1213_idx` ON `band_bandpost` (`created_at` DESC);
--
-- Create index band_bandco_post_id_c4e0b5_idx on field(s) post of model bandcomment
--
CREATE INDEX `band_bandco_post_id_c4e0b5_idx` ON `band_bandcomment` (`post_id`);
--
-- Create index band_bandco_author__5bbe03_idx on field(s) author of model bandcomment
--
CREATE INDEX `band_bandco_author__5bbe03_idx` ON `band_bandcomment` (`author_id`);
--
-- Create index band_bandco_parent__f605f1_idx on field(s) parent of model bandcomment
--
CREATE INDEX `band_bandco_parent__f605f1_idx` ON `band_bandcomment` (`parent_id`);
--
-- Create index band_bandco_created_07143a_idx on field(s) -created_at of model bandcomment
--
CREATE INDEX `band_bandco_created_07143a_idx` ON `band_bandcomment` (`created_at` DESC);
--
-- Create index band_bandpo_post_id_de2477_idx on field(s) post of model bandpostimage
--
CREATE INDEX `band_bandpo_post_id_de2477_idx` ON `band_bandpostimage` (`post_id`);
--
-- Create index band_bandpo_post_id_a758b8_idx on field(s) post, order_index of model bandpostimage
--
CREATE INDEX `band_bandpo_post_id_a758b8_idx` ON `band_bandpostimage` (`post_id`, `order_index`);
--
-- Create index band_bandpo_post_id_28de87_idx on field(s) post of model bandpostlike
--
CREATE INDEX `band_bandpo_post_id_28de87_idx` ON `band_bandpostlike` (`post_id`);
--
-- Create index band_bandpo_user_id_2340a7_idx on field(s) user of model bandpostlike
--
CREATE INDEX `band_bandpo_user_id_2340a7_idx` ON `band_bandpostlike` (`user_id`);
--
-- Alter unique_together for bandpostlike (1 constraint(s))
--
ALTER TABLE `band_bandpostlike` ADD CONSTRAINT `band_bandpostlike_post_id_user_id_6032444f_uniq` UNIQUE (`post_id`, `user_id`);
--
-- Create index band_bandsc_band_id_e8d32a_idx on field(s) band of model bandschedule
--
CREATE INDEX `band_bandsc_band_id_e8d32a_idx` ON `band_bandschedule` (`band_id`);
--
-- Create index band_bandsc_post_id_ef3715_idx on field(s) post of model bandschedule
--
CREATE INDEX `band_bandsc_post_id_ef3715_idx` ON `band_bandschedule` (`post_id`);
--
-- Create index band_bandsc_start_d_a0274e_idx on field(s) start_datetime of model bandschedule
--
CREATE INDEX `band_bandsc_start_d_a0274e_idx` ON `band_bandschedule` (`start_datetime`);
--
-- Create index band_bandsc_created_d7569b_idx on field(s) created_by of model bandschedule
--
CREATE INDEX `band_bandsc_created_d7569b_idx` ON `band_bandschedule` (`created_by_id`);
--
-- Create index band_bandsc_applica_928ad6_idx on field(s) application_deadline of model bandschedule
--
CREATE INDEX `band_bandsc_applica_928ad6_idx` ON `band_bandschedule` (`application_deadline`);
--
-- Create index band_bandsc_schedul_66c378_idx on field(s) schedule of model bandscheduleapplication
--
CREATE INDEX `band_bandsc_schedul_66c378_idx` ON `band_bandscheduleapplication` (`schedule_id`);
--
-- Create index band_bandsc_user_id_32fd78_idx on field(s) user of model bandscheduleapplication
--
CREATE INDEX `band_bandsc_user_id_32fd78_idx` ON `band_bandscheduleapplication` (`user_id`);
--
-- Create index band_bandsc_status_0630b8_idx on field(s) status of model bandscheduleapplication
--
CREATE INDEX `band_bandsc_status_0630b8_idx` ON `band_bandscheduleapplication` (`status`);
--
-- Create index band_bandsc_applied_e76bde_idx on field(s) -applied_at of model bandscheduleapplication
--
CREATE INDEX `band_bandsc_applied_e76bde_idx` ON `band_bandscheduleapplication` (`applied_at` DESC);
--
-- Create index band_bandsc_reviewe_e7af79_idx on field(s) reviewed_by of model bandscheduleapplication
--
CREATE INDEX `band_bandsc_reviewe_e7af79_idx` ON `band_bandscheduleapplication` (`reviewed_by_id`);
--
-- Alter unique_together for bandscheduleapplication (1 constraint(s))
--
ALTER TABLE `band_bandscheduleapplication` ADD CONSTRAINT `band_bandscheduleapplication_schedule_id_user_id_b810600d_uniq` UNIQUE (`schedule_id`, `user_id`);
--
-- Create index band_bandvo_post_id_bc07d7_idx on field(s) post of model bandvote
--
CREATE INDEX `band_bandvo_post_id_bc07d7_idx` ON `band_bandvote` (`post_id`);
--
-- Create index band_bandvo_end_dat_30d1a2_idx on field(s) end_datetime of model bandvote
--
CREATE INDEX `band_bandvo_end_dat_30d1a2_idx` ON `band_bandvote` (`end_datetime`);
--
-- Create index band_bandvo_vote_id_9937d3_idx on field(s) vote of model bandvoteoption
--
CREATE INDEX `band_bandvo_vote_id_9937d3_idx` ON `band_bandvoteoption` (`vote_id`);
--
-- Create index band_bandvo_vote_id_0d90e6_idx on field(s) vote, order_index of model bandvoteoption
--
CREATE INDEX `band_bandvo_vote_id_0d90e6_idx` ON `band_bandvoteoption` (`vote_id`, `order_index`);
--
-- Create index band_bandvo_vote_id_0531e3_idx on field(s) vote of model bandvotechoice
--
CREATE INDEX `band_bandvo_vote_id_0531e3_idx` ON `band_bandvotechoice` (`vote_id`);
--
-- Create index band_bandvo_option__85e2f5_idx on field(s) option of model bandvotechoice
--
CREATE INDEX `band_bandvo_option__85e2f5_idx` ON `band_bandvotechoice` (`option_id`);
--
-- Create index band_bandvo_user_id_aa28d5_idx on field(s) user of model bandvotechoice
--
CREATE INDEX `band_bandvo_user_id_aa28d5_idx` ON `band_bandvotechoice` (`user_id`);
--
-- Alter unique_together for bandvotechoice (1 constraint(s))
--
ALTER TABLE `band_bandvotechoice` ADD CONSTRAINT `band_bandvotechoice_vote_id_user_id_option_id_2aa8be43_uniq` UNIQUE (`vote_id`, `user_id`, `option_id`);
ALTER TABLE `band_band` ADD CONSTRAINT `band_band_created_by_id_1e3821b4_fk_accounts_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_user` (`id`);
ALTER TABLE `band_bandcomment` ADD CONSTRAINT `band_bandcomment_author_id_8c65343b_fk_accounts_user_id` FOREIGN KEY (`author_id`) REFERENCES `accounts_user` (`id`);
ALTER TABLE `band_bandcomment` ADD CONSTRAINT `band_bandcomment_parent_id_d73677e6_fk_band_bandcomment_id` FOREIGN KEY (`parent_id`) REFERENCES `band_bandcomment` (`id`);
ALTER TABLE `band_bandcommentlike` ADD CONSTRAINT `band_bandcommentlike_comment_id_dbb078ba_fk_band_bandcomment_id` FOREIGN KEY (`comment_id`) REFERENCES `band_bandcomment` (`id`);
ALTER TABLE `band_bandcommentlike` ADD CONSTRAINT `band_bandcommentlike_user_id_344d06ce_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`);
ALTER TABLE `band_bandmember` ADD CONSTRAINT `band_bandmember_band_id_b0c50438_fk_band_band_id` FOREIGN KEY (`band_id`) REFERENCES `band_band` (`id`);
ALTER TABLE `band_bandmember` ADD CONSTRAINT `band_bandmember_user_id_d58c293a_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`);
ALTER TABLE `band_bandpost` ADD CONSTRAINT `band_bandpost_author_id_cbf93e3e_fk_accounts_user_id` FOREIGN KEY (`author_id`) REFERENCES `accounts_user` (`id`);
ALTER TABLE `band_bandpost` ADD CONSTRAINT `band_bandpost_band_id_173bbce3_fk_band_band_id` FOREIGN KEY (`band_id`) REFERENCES `band_band` (`id`);
ALTER TABLE `band_bandpostimage` ADD CONSTRAINT `band_bandpostimage_post_id_84274863_fk_band_bandpost_id` FOREIGN KEY (`post_id`) REFERENCES `band_bandpost` (`id`);
ALTER TABLE `band_bandpostlike` ADD CONSTRAINT `band_bandpostlike_post_id_331e89b3_fk_band_bandpost_id` FOREIGN KEY (`post_id`) REFERENCES `band_bandpost` (`id`);
ALTER TABLE `band_bandpostlike` ADD CONSTRAINT `band_bandpostlike_user_id_6449feed_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`);
ALTER TABLE `band_bandschedule` ADD CONSTRAINT `band_bandschedule_band_id_e9849d1d_fk_band_band_id` FOREIGN KEY (`band_id`) REFERENCES `band_band` (`id`);
ALTER TABLE `band_bandschedule` ADD CONSTRAINT `band_bandschedule_created_by_id_e1b5d87d_fk_accounts_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_user` (`id`);
ALTER TABLE `band_bandschedule` ADD CONSTRAINT `band_bandschedule_post_id_c65c8b1d_fk_band_bandpost_id` FOREIGN KEY (`post_id`) REFERENCES `band_bandpost` (`id`);
ALTER TABLE `band_bandscheduleapplication` ADD CONSTRAINT `band_bandscheduleapp_reviewed_by_id_ab985f92_fk_accounts_` FOREIGN KEY (`reviewed_by_id`) REFERENCES `accounts_user` (`id`);
ALTER TABLE `band_bandscheduleapplication` ADD CONSTRAINT `band_bandscheduleapp_schedule_id_a2ed5663_fk_band_band` FOREIGN KEY (`schedule_id`) REFERENCES `band_bandschedule` (`id`);
ALTER TABLE `band_bandscheduleapplication` ADD CONSTRAINT `band_bandscheduleapp_user_id_734a6359_fk_accounts_` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`);
ALTER TABLE `band_bandvote` ADD CONSTRAINT `band_bandvote_post_id_32bc7e5a_fk_band_bandpost_id` FOREIGN KEY (`post_id`) REFERENCES `band_bandpost` (`id`);
ALTER TABLE `band_bandvoteoption` ADD CONSTRAINT `band_bandvoteoption_vote_id_2af6388e_fk_band_bandvote_id` FOREIGN KEY (`vote_id`) REFERENCES `band_bandvote` (`id`);
ALTER TABLE `band_bandvotechoice` ADD CONSTRAINT `band_bandvotechoice_user_id_a7b911f6_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`);
ALTER TABLE `band_bandvotechoice` ADD CONSTRAINT `band_bandvotechoice_vote_id_e1947256_fk_band_bandvote_id` FOREIGN KEY (`vote_id`) REFERENCES `band_bandvote` (`id`);
ALTER TABLE `band_bandvotechoice` ADD CONSTRAINT `band_bandvotechoice_option_id_86383e78_fk_band_bandvoteoption_id` FOREIGN KEY (`option_id`) REFERENCES `band_bandvoteoption` (`id`);


-- Migration: band.0002_band_band_type
--
-- Add field band_type to band
--
ALTER TABLE `band_band` ADD COLUMN `band_type` varchar(20) DEFAULT 'group' NOT NULL;
ALTER TABLE `band_band` ALTER COLUMN `band_type` DROP DEFAULT;


-- Migration: band.0003_band_region
--
-- Add field region to band
--
ALTER TABLE `band_band` ADD COLUMN `region` varchar(20) DEFAULT 'all' NOT NULL;
ALTER TABLE `band_band` ALTER COLUMN `region` DROP DEFAULT;


-- Migration: band.0004_alter_band_region
--
-- Alter field region on band
--
-- (no-op)


-- Migration: band.0005_band_flash_region_detail
--
-- Add field flash_region_detail to band
--
ALTER TABLE `band_band` ADD COLUMN `flash_region_detail` varchar(20) DEFAULT '' NOT NULL;
ALTER TABLE `band_band` ALTER COLUMN `flash_region_detail` DROP DEFAULT;


-- Migration: band.0006_band_categories_alter_band_band_type
--
-- Add field categories to band
--
ALTER TABLE `band_band` ADD COLUMN `categories` varchar(100) DEFAULT '' NOT NULL;
ALTER TABLE `band_band` ALTER COLUMN `categories` DROP DEFAULT;
--
-- Alter field band_type on band
--
-- (no-op)


-- Migration: band.0007_band_approved_at_band_approved_by_band_is_approved_and_more
--
-- Add field approved_at to band
--
ALTER TABLE `band_band` ADD COLUMN `approved_at` datetime(6) NULL;
--
-- Add field approved_by to band
--
ALTER TABLE `band_band` ADD COLUMN `approved_by_id` bigint NULL , ADD CONSTRAINT `band_band_approved_by_id_3e3ae1a5_fk_accounts_user_id` FOREIGN KEY (`approved_by_id`) REFERENCES `accounts_user`(`id`);
--
-- Add field is_approved to band
--
ALTER TABLE `band_band` ADD COLUMN `is_approved` bool DEFAULT 1 NOT NULL;
ALTER TABLE `band_band` ALTER COLUMN `is_approved` DROP DEFAULT;
--
-- Add field rejection_reason to band
--
ALTER TABLE `band_band` ADD COLUMN `rejection_reason` longtext NOT NULL;
--
-- Alter field region on band
--
-- (no-op)
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL


-- Migration: band.0009_band_detailed_description_alter_band_description
--
-- Add field detailed_description to band
--
ALTER TABLE `band_band` ADD COLUMN `detailed_description` longtext NOT NULL;
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
--
-- Alter field description on band
--
ALTER TABLE `band_band` MODIFY `description` varchar(500) NOT NULL;


-- Migration: band.0010_alter_bandmember_role_alter_bandpost_post_type
--
-- Alter field role on bandmember
--
-- (no-op)
--
-- Alter field post_type on bandpost
--
-- (no-op)


-- Migration: band.0011_alter_bandpostimage_post
--
-- Alter field post on bandpostimage
--
ALTER TABLE `band_bandpostimage` DROP FOREIGN KEY `band_bandpostimage_post_id_84274863_fk_band_bandpost_id`;
ALTER TABLE `band_bandpostimage` MODIFY `post_id` bigint NULL;
ALTER TABLE `band_bandpostimage` ADD CONSTRAINT `band_bandpostimage_post_id_84274863_fk_band_bandpost_id` FOREIGN KEY (`post_id`) REFERENCES `band_bandpost` (`id`);


-- Migration: band.0012_bandscheduleimage
--
-- Create model BandScheduleImage
--
CREATE TABLE `band_bandscheduleimage` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `image` varchar(100) NOT NULL, `order` integer NOT NULL, `created_at` datetime(6) NOT NULL, `schedule_id` bigint NOT NULL);
ALTER TABLE `band_bandscheduleimage` ADD CONSTRAINT `band_bandscheduleima_schedule_id_92f4e110_fk_band_band` FOREIGN KEY (`schedule_id`) REFERENCES `band_bandschedule` (`id`);
CREATE INDEX `band_bandsc_schedul_3b0667_idx` ON `band_bandscheduleimage` (`schedule_id`, `order`);


-- Migration: band.0013_band_deletion_approved_at_band_deletion_approved_by_and_more
--
-- Add field deletion_approved_at to band
--
ALTER TABLE `band_band` ADD COLUMN `deletion_approved_at` datetime(6) NULL;
--
-- Add field deletion_approved_by to band
--
ALTER TABLE `band_band` ADD COLUMN `deletion_approved_by_id` bigint NULL , ADD CONSTRAINT `band_band_deletion_approved_by_id_1f5e3b67_fk_accounts_user_id` FOREIGN KEY (`deletion_approved_by_id`) REFERENCES `accounts_user`(`id`);
--
-- Add field deletion_reason to band
--
ALTER TABLE `band_band` ADD COLUMN `deletion_reason` longtext NOT NULL;
--
-- Add field deletion_requested to band
--
ALTER TABLE `band_band` ADD COLUMN `deletion_requested` bool DEFAULT 0 NOT NULL;
ALTER TABLE `band_band` ALTER COLUMN `deletion_requested` DROP DEFAULT;
--
-- Add field deletion_requested_at to band
--
ALTER TABLE `band_band` ADD COLUMN `deletion_requested_at` datetime(6) NULL;


-- Migration: community.0001_initial
--
-- Create model Post
--
CREATE TABLE `community_post` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `title` varchar(200) NOT NULL, `category` varchar(20) NOT NULL, `content` longtext NOT NULL, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `view_count` integer UNSIGNED NOT NULL CHECK (`view_count` >= 0), `like_count` integer UNSIGNED NOT NULL CHECK (`like_count` >= 0), `comment_count` integer UNSIGNED NOT NULL CHECK (`comment_count` >= 0), `is_deleted` bool NOT NULL, `is_pinned` bool NOT NULL, `author_id` bigint NOT NULL);
CREATE TABLE `community_post_likes` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `post_id` bigint NOT NULL, `user_id` bigint NOT NULL);
--
-- Create model Comment
--
CREATE TABLE `community_comment` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `content` longtext NOT NULL, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `like_count` integer UNSIGNED NOT NULL CHECK (`like_count` >= 0), `is_deleted` bool NOT NULL, `author_id` bigint NOT NULL, `parent_id` bigint NULL, `post_id` bigint NOT NULL);
CREATE TABLE `community_comment_likes` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `comment_id` bigint NOT NULL, `user_id` bigint NOT NULL);
--
-- Create model PostImage
--
CREATE TABLE `community_postimage` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `image` varchar(100) NOT NULL, `order` integer UNSIGNED NOT NULL CHECK (`order` >= 0), `created_at` datetime(6) NOT NULL, `post_id` bigint NOT NULL);
--
-- Create model PostShare
--
CREATE TABLE `community_postshare` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `shared_at` datetime(6) NOT NULL, `post_id` bigint NOT NULL, `user_id` bigint NOT NULL);
--
-- Create index community_p_created_6febb2_idx on field(s) -created_at of model post
--
CREATE INDEX `community_p_created_6febb2_idx` ON `community_post` (`created_at` DESC);
--
-- Create index community_p_categor_0dbe3e_idx on field(s) category of model post
--
CREATE INDEX `community_p_categor_0dbe3e_idx` ON `community_post` (`category`);
--
-- Create index community_p_author__5261da_idx on field(s) author of model post
--
CREATE INDEX `community_p_author__5261da_idx` ON `community_post` (`author_id`);
--
-- Create index community_c_post_id_bea033_idx on field(s) post, created_at of model comment
--
CREATE INDEX `community_c_post_id_bea033_idx` ON `community_comment` (`post_id`, `created_at`);
--
-- Create index community_c_author__1e6995_idx on field(s) author of model comment
--
CREATE INDEX `community_c_author__1e6995_idx` ON `community_comment` (`author_id`);
--
-- Create index community_c_parent__5a3862_idx on field(s) parent of model comment
--
CREATE INDEX `community_c_parent__5a3862_idx` ON `community_comment` (`parent_id`);
--
-- Create index community_p_post_id_b89cc2_idx on field(s) post, order of model postimage
--
CREATE INDEX `community_p_post_id_b89cc2_idx` ON `community_postimage` (`post_id`, `order`);
--
-- Create index community_p_post_id_1686b9_idx on field(s) post of model postshare
--
CREATE INDEX `community_p_post_id_1686b9_idx` ON `community_postshare` (`post_id`);
--
-- Create index community_p_user_id_f8f7f7_idx on field(s) user of model postshare
--
CREATE INDEX `community_p_user_id_f8f7f7_idx` ON `community_postshare` (`user_id`);
--
-- Alter unique_together for postshare (1 constraint(s))
--
ALTER TABLE `community_postshare` ADD CONSTRAINT `community_postshare_post_id_user_id_0aa98512_uniq` UNIQUE (`post_id`, `user_id`);
ALTER TABLE `community_post` ADD CONSTRAINT `community_post_author_id_a6c5f564_fk_accounts_user_id` FOREIGN KEY (`author_id`) REFERENCES `accounts_user` (`id`);
ALTER TABLE `community_post_likes` ADD CONSTRAINT `community_post_likes_post_id_user_id_7155e6ea_uniq` UNIQUE (`post_id`, `user_id`);
ALTER TABLE `community_post_likes` ADD CONSTRAINT `community_post_likes_post_id_3dbbbf10_fk_community_post_id` FOREIGN KEY (`post_id`) REFERENCES `community_post` (`id`);
ALTER TABLE `community_post_likes` ADD CONSTRAINT `community_post_likes_user_id_88523dbc_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`);
ALTER TABLE `community_comment` ADD CONSTRAINT `community_comment_author_id_51c65c2a_fk_accounts_user_id` FOREIGN KEY (`author_id`) REFERENCES `accounts_user` (`id`);
ALTER TABLE `community_comment` ADD CONSTRAINT `community_comment_parent_id_2fd9f894_fk_community_comment_id` FOREIGN KEY (`parent_id`) REFERENCES `community_comment` (`id`);
ALTER TABLE `community_comment` ADD CONSTRAINT `community_comment_post_id_12b521a8_fk_community_post_id` FOREIGN KEY (`post_id`) REFERENCES `community_post` (`id`);
ALTER TABLE `community_comment_likes` ADD CONSTRAINT `community_comment_likes_comment_id_user_id_ddb824a0_uniq` UNIQUE (`comment_id`, `user_id`);
ALTER TABLE `community_comment_likes` ADD CONSTRAINT `community_comment_li_comment_id_3ec95328_fk_community` FOREIGN KEY (`comment_id`) REFERENCES `community_comment` (`id`);
ALTER TABLE `community_comment_likes` ADD CONSTRAINT `community_comment_likes_user_id_3d69d764_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`);
ALTER TABLE `community_postimage` ADD CONSTRAINT `community_postimage_post_id_bb183c06_fk_community_post_id` FOREIGN KEY (`post_id`) REFERENCES `community_post` (`id`);
ALTER TABLE `community_postshare` ADD CONSTRAINT `community_postshare_post_id_085b84c5_fk_community_post_id` FOREIGN KEY (`post_id`) REFERENCES `community_post` (`id`);
ALTER TABLE `community_postshare` ADD CONSTRAINT `community_postshare_user_id_1cad0464_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`);


-- Migration: community.0002_category_remove_post_community_p_categor_0dbe3e_idx_and_more
--
-- Create model Category
--
CREATE TABLE `community_category` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `name` varchar(50) NOT NULL UNIQUE, `slug` varchar(50) NOT NULL UNIQUE, `display_order` integer UNSIGNED NOT NULL CHECK (`display_order` >= 0), `is_active` bool NOT NULL, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL);
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
--
-- Add field _old_category to post
--
ALTER TABLE `community_post` ADD COLUMN `_old_category` varchar(20) NULL;
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
--
-- Remove index community_p_categor_0dbe3e_idx from post
--
DROP INDEX `community_p_categor_0dbe3e_idx` ON `community_post`;
--
-- Alter field category on post
--
ALTER TABLE `community_post` RENAME COLUMN `category` TO `category_id`;
ALTER TABLE `community_post` MODIFY `category_id` bigint NOT NULL;
ALTER TABLE `community_post` MODIFY `category_id` bigint NULL;
CREATE INDEX `community_post_category_id_40d6514d` ON `community_post` (`category_id`);
ALTER TABLE `community_post` ADD CONSTRAINT `community_post_category_id_40d6514d_fk_community_category_id` FOREIGN KEY (`category_id`) REFERENCES `community_category` (`id`);
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
--
-- Remove field _old_category from post
--
ALTER TABLE `community_post` DROP COLUMN `_old_category`;
--
-- Create index community_c_slug_777ae5_idx on field(s) slug of model category
--
CREATE INDEX `community_c_slug_777ae5_idx` ON `community_category` (`slug`);
--
-- Create index community_c_is_acti_5c99dc_idx on field(s) is_active, display_order of model category
--
CREATE INDEX `community_c_is_acti_5c99dc_idx` ON `community_category` (`is_active`, `display_order`);
--
-- Create index community_p_categor_d5bd82_idx on field(s) category, -created_at of model post
--
CREATE INDEX `community_p_categor_d5bd82_idx` ON `community_post` (`category_id`, `created_at` DESC);
--
-- Create index community_p_view_co_b34b52_idx on field(s) -view_count of model post
--
CREATE INDEX `community_p_view_co_b34b52_idx` ON `community_post` (`view_count` DESC);


-- Migration: community.0003_create_initial_categories
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL


-- Migration: community.0004_fix_category_foreignkey
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
--
-- Alter field category on post
--
-- (no-op)


-- Migration: community.0005_post_source_post_community_p_source_ece6fc_idx
--
-- Add field source to post
--
ALTER TABLE `community_post` ADD COLUMN `source` varchar(20) DEFAULT 'community' NOT NULL;
ALTER TABLE `community_post` ALTER COLUMN `source` DROP DEFAULT;
--
-- Create index community_p_source_ece6fc_idx on field(s) source, -created_at of model post
--
CREATE INDEX `community_p_source_ece6fc_idx` ON `community_post` (`source`, `created_at` DESC);


-- Migration: community.0006_alter_post_source
--
-- Alter field source on post
--
-- (no-op)


-- Migration: community.0007_badmintokpost_communitypost
--
-- Create proxy model BadmintokPost
--
-- (no-op)
--
-- Create proxy model CommunityPost
--
-- (no-op)


-- Migration: community.0008_create_badmintok_categories
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL


-- Migration: community.0009_alter_communitypost_options_post_published_at_and_more
--
-- Change Meta options on communitypost
--
-- (no-op)
--
-- Add field published_at to post
--
ALTER TABLE `community_post` ADD COLUMN `published_at` datetime(6) NULL;
--
-- Add field slug to post
--
ALTER TABLE `community_post` ADD COLUMN `slug` varchar(200) DEFAULT '' NOT NULL;
ALTER TABLE `community_post` ALTER COLUMN `slug` DROP DEFAULT;
--
-- Add field thumbnail to post
--
ALTER TABLE `community_post` ADD COLUMN `thumbnail` varchar(100) NULL;
--
-- Alter field source on post
--
-- (no-op)
--
-- Create index community_p_slug_614d88_idx on field(s) slug of model post
--
CREATE INDEX `community_p_slug_614d88_idx` ON `community_post` (`slug`);
--
-- Create index community_p_publish_9a7d6d_idx on field(s) published_at of model post
--
CREATE INDEX `community_p_publish_9a7d6d_idx` ON `community_post` (`published_at`);
CREATE INDEX `community_post_slug_1c7322e5` ON `community_post` (`slug`);


-- Migration: community.0010_category_parent_and_more
--
-- Add field parent to category
--
ALTER TABLE `community_category` ADD COLUMN `parent_id` bigint NULL , ADD CONSTRAINT `community_category_parent_id_f769c6e3_fk_community_category_id` FOREIGN KEY (`parent_id`) REFERENCES `community_category`(`id`);
--
-- Create index community_c_parent__eb9340_idx on field(s) parent of model category
--
CREATE INDEX `community_c_parent__eb9340_idx` ON `community_category` (`parent_id`);


-- Migration: community.0011_post_focus_keyword_post_is_draft_and_more
--
-- Add field focus_keyword to post
--
ALTER TABLE `community_post` ADD COLUMN `focus_keyword` varchar(100) DEFAULT '' NOT NULL;
ALTER TABLE `community_post` ALTER COLUMN `focus_keyword` DROP DEFAULT;
--
-- Add field is_draft to post
--
ALTER TABLE `community_post` ADD COLUMN `is_draft` bool DEFAULT 0 NOT NULL;
ALTER TABLE `community_post` ALTER COLUMN `is_draft` DROP DEFAULT;
--
-- Add field meta_description to post
--
ALTER TABLE `community_post` ADD COLUMN `meta_description` longtext NOT NULL;


-- Migration: community.0012_post_thumbnail_alt
--
-- Add field thumbnail_alt to post
--
ALTER TABLE `community_post` ADD COLUMN `thumbnail_alt` varchar(200) DEFAULT '' NOT NULL;
ALTER TABLE `community_post` ALTER COLUMN `thumbnail_alt` DROP DEFAULT;


-- Migration: community.0013_alter_post_slug
--
-- Alter field slug on post
--
ALTER TABLE `community_post` MODIFY `slug` varchar(45) NOT NULL;


-- Migration: contests.0001_initial
--
-- Create model Contest
--
CREATE TABLE `contests_contest` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `title` varchar(200) NOT NULL, `slug` varchar(50) NOT NULL UNIQUE, `image` varchar(100) NULL, `schedule_start` date NOT NULL, `schedule_end` date NULL, `location` varchar(200) NOT NULL, `event_division` varchar(255) NOT NULL, `registration_start` date NOT NULL, `registration_end` date NOT NULL, `entry_fee` varchar(100) NOT NULL, `competition_type` varchar(100) NOT NULL, `participant_reward` varchar(255) NOT NULL, `sponsor` varchar(255) NOT NULL, `award_reward` varchar(255) NOT NULL, `registration_link` varchar(200) NOT NULL, `description` longtext NOT NULL, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL);


-- Migration: contests.0002_contestcategory_contest_category
--
-- Create model ContestCategory
--
CREATE TABLE `contests_contestcategory` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `name` varchar(100) NOT NULL, `color` varchar(7) NOT NULL, `description` varchar(255) NOT NULL);
--
-- Add field category to contest
--
ALTER TABLE `contests_contest` ADD COLUMN `category_id` bigint NULL , ADD CONSTRAINT `contests_contest_category_id_8d9e930e_fk_contests_` FOREIGN KEY (`category_id`) REFERENCES `contests_contestcategory`(`id`);


-- Migration: contests.0003_alter_contest_award_reward
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
--
-- Alter field award_reward on contest
--
ALTER TABLE `contests_contest` MODIFY `award_reward` json NOT NULL;
ALTER TABLE `contests_contest` MODIFY `award_reward` json NULL;


-- Migration: contests.0004_contest_is_qualifying
--
-- Add field is_qualifying to contest
--
ALTER TABLE `contests_contest` ADD COLUMN `is_qualifying` bool DEFAULT 0 NOT NULL;
ALTER TABLE `contests_contest` ALTER COLUMN `is_qualifying` DROP DEFAULT;


-- Migration: contests.0005_contest_game_events
--
-- Add field game_events to contest
--
ALTER TABLE `contests_contest` ADD COLUMN `game_events` json NULL;


-- Migration: contests.0006_contest_age_group_contest_event_type_contest_grade
--
-- Add field age_group to contest
--
ALTER TABLE `contests_contest` ADD COLUMN `age_group` varchar(100) DEFAULT '' NOT NULL;
ALTER TABLE `contests_contest` ALTER COLUMN `age_group` DROP DEFAULT;
--
-- Add field event_type to contest
--
ALTER TABLE `contests_contest` ADD COLUMN `event_type` varchar(100) DEFAULT '' NOT NULL;
ALTER TABLE `contests_contest` ALTER COLUMN `event_type` DROP DEFAULT;
--
-- Add field grade to contest
--
ALTER TABLE `contests_contest` ADD COLUMN `grade` varchar(100) DEFAULT '' NOT NULL;
ALTER TABLE `contests_contest` ALTER COLUMN `grade` DROP DEFAULT;


-- Migration: contests.0007_contest_schedule_details
--
-- Add field schedule_details to contest
--
ALTER TABLE `contests_contest` ADD COLUMN `schedule_details` json NULL;


-- Migration: contests.0008_contest_registration_name
--
-- Add field registration_name to contest
--
ALTER TABLE `contests_contest` ADD COLUMN `registration_name` varchar(200) DEFAULT '' NOT NULL;
ALTER TABLE `contests_contest` ALTER COLUMN `registration_name` DROP DEFAULT;


-- Migration: contests.0009_contestschedule
--
-- Create model ContestSchedule
--
CREATE TABLE `contests_contestschedule` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `date` date NOT NULL, `events` json NULL, `ages` json NULL, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `contest_id` bigint NOT NULL);
ALTER TABLE `contests_contestschedule` ADD CONSTRAINT `contests_contestsche_contest_id_de6931dd_fk_contests_` FOREIGN KEY (`contest_id`) REFERENCES `contests_contest` (`id`);


-- Migration: contests.0010_remove_contest_age_group_remove_contest_event_type_and_more
--
-- Remove field age_group from contest
--
ALTER TABLE `contests_contest` DROP COLUMN `age_group`;
--
-- Remove field event_type from contest
--
ALTER TABLE `contests_contest` DROP COLUMN `event_type`;
--
-- Remove field game_events from contest
--
ALTER TABLE `contests_contest` DROP COLUMN `game_events`;
--
-- Remove field grade from contest
--
ALTER TABLE `contests_contest` DROP COLUMN `grade`;
--
-- Remove field schedule_details from contest
--
ALTER TABLE `contests_contest` DROP COLUMN `schedule_details`;


-- Migration: contests.0011_contest_award_reward_text_contest_grade_division_and_more
--
-- Add field award_reward_text to contest
--
ALTER TABLE `contests_contest` ADD COLUMN `award_reward_text` longtext NOT NULL;
--
-- Add field grade_division to contest
--
ALTER TABLE `contests_contest` ADD COLUMN `grade_division` longtext NOT NULL;
--
-- Add field participant_target to contest
--
ALTER TABLE `contests_contest` ADD COLUMN `participant_target` longtext NOT NULL;
--
-- Alter field description on contest
--
-- (no-op)


-- Migration: contests.0012_remove_contest_grade_division_and_more
--
-- Remove field grade_division from contest
--
ALTER TABLE `contests_contest` DROP COLUMN `grade_division`;
--
-- Alter field participant_target on contest
--
-- (no-op)


-- Migration: contests.0013_contest_likes
--
-- Add field likes to contest
--
CREATE TABLE `contests_contest_likes` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `contest_id` bigint NOT NULL, `user_id` bigint NOT NULL);
ALTER TABLE `contests_contest_likes` ADD CONSTRAINT `contests_contest_likes_contest_id_user_id_7a351abe_uniq` UNIQUE (`contest_id`, `user_id`);
ALTER TABLE `contests_contest_likes` ADD CONSTRAINT `contests_contest_lik_contest_id_68b60daf_fk_contests_` FOREIGN KEY (`contest_id`) REFERENCES `contests_contest` (`id`);
ALTER TABLE `contests_contest_likes` ADD CONSTRAINT `contests_contest_likes_user_id_95523924_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`);


-- Migration: contests.0014_sponsor_alter_contest_sponsor
--
-- Create model Sponsor
--
CREATE TABLE `contests_sponsor` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `name` varchar(100) NOT NULL UNIQUE);
--
-- Rename field sponsor on contest to sponsor_old
--
ALTER TABLE `contests_contest` RENAME COLUMN `sponsor` TO `sponsor_old`;
--
-- Add field sponsor_new to contest
--
ALTER TABLE `contests_contest` ADD COLUMN `sponsor_new_id` bigint NULL , ADD CONSTRAINT `contests_contest_sponsor_new_id_06b22f9c_fk_contests_sponsor_id` FOREIGN KEY (`sponsor_new_id`) REFERENCES `contests_sponsor`(`id`);
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
--
-- Remove field sponsor_old from contest
--
ALTER TABLE `contests_contest` DROP COLUMN `sponsor_old`;
--
-- Rename field sponsor_new on contest to sponsor
--
ALTER TABLE `contests_contest` RENAME COLUMN `sponsor_new_id` TO `sponsor_id`;


-- Migration: contests.0015_add_initial_sponsors
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL


-- Migration: contests.0016_contest_map_url_contest_region_and_more
--
-- Add field map_url to contest
--
ALTER TABLE `contests_contest` ADD COLUMN `map_url` varchar(200) DEFAULT '' NOT NULL;
ALTER TABLE `contests_contest` ALTER COLUMN `map_url` DROP DEFAULT;
--
-- Add field region to contest
--
ALTER TABLE `contests_contest` ADD COLUMN `region` varchar(20) DEFAULT '' NOT NULL;
ALTER TABLE `contests_contest` ALTER COLUMN `region` DROP DEFAULT;
--
-- Alter field location on contest
--
-- (no-op)


-- Migration: contests.0017_alter_contest_location
--
-- Alter field location on contest
--
-- (no-op)


-- Migration: contests.0018_remove_contest_map_url_remove_contest_region_and_more
--
-- Remove field map_url from contest
--
ALTER TABLE `contests_contest` DROP COLUMN `map_url`;
--
-- Remove field region from contest
--
ALTER TABLE `contests_contest` DROP COLUMN `region`;
--
-- Alter field location on contest
--
-- (no-op)


-- Migration: contests.0019_alter_contest_slug
--
-- Alter field slug on contest
--
ALTER TABLE `contests_contest` MODIFY `slug` varchar(75) NOT NULL;


-- Migration: contests.0020_alter_contest_slug
--
-- Alter field slug on contest
--
ALTER TABLE `contests_contest` MODIFY `slug` varchar(80) NOT NULL;


-- Migration: contests.0021_alter_contest_slug
--
-- Alter field slug on contest
--
ALTER TABLE `contests_contest` MODIFY `slug` varchar(45) NOT NULL;


-- Migration: contests.0022_contestimage
--
-- Create model ContestImage
--
CREATE TABLE `contests_contestimage` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `image` varchar(100) NOT NULL, `order` integer UNSIGNED NOT NULL CHECK (`order` >= 0), `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `contest_id` bigint NOT NULL);
ALTER TABLE `contests_contestimage` ADD CONSTRAINT `contests_contestimage_contest_id_3567341b_fk_contests_contest_id` FOREIGN KEY (`contest_id`) REFERENCES `contests_contest` (`id`);


-- Migration: contests.0023_remove_contestimage_updated_at_and_more
--
-- Remove field updated_at from contestimage
--
ALTER TABLE `contests_contestimage` DROP COLUMN `updated_at`;
--
-- Alter field order on contestimage
--
-- (no-op)


-- Migration: contests.0024_remove_contest_location_contest_region_and_more
--
-- Remove field location from contest
--
ALTER TABLE `contests_contest` DROP COLUMN `location`;
--
-- Add field region to contest
--
ALTER TABLE `contests_contest` ADD COLUMN `region` varchar(20) DEFAULT 'all' NOT NULL;
ALTER TABLE `contests_contest` ALTER COLUMN `region` DROP DEFAULT;
--
-- Add field region_detail to contest
--
ALTER TABLE `contests_contest` ADD COLUMN `region_detail` varchar(200) DEFAULT '' NOT NULL;
ALTER TABLE `contests_contest` ALTER COLUMN `region_detail` DROP DEFAULT;


-- Migration: contests.0025_alter_contest_region
--
-- Alter field region on contest
--
-- (no-op)


-- Migration: badmintok.0001_initial
--
-- Create model BadmintokBanner
--
CREATE TABLE `badmintok_badmintokbanner` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `title` varchar(100) NOT NULL, `image` varchar(100) NOT NULL, `link_url` varchar(200) NOT NULL, `alt_text` varchar(255) NOT NULL, `is_active` bool NOT NULL, `display_order` integer UNSIGNED NOT NULL CHECK (`display_order` >= 0), `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL);


-- Migration: badmintok.0002_notice
--
-- Create model Notice
--
CREATE TABLE `badmintok_notice` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `title` varchar(200) NOT NULL, `content` longtext NOT NULL, `is_pinned` bool NOT NULL, `view_count` integer UNSIGNED NOT NULL CHECK (`view_count` >= 0), `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `author_id` bigint NOT NULL);
ALTER TABLE `badmintok_notice` ADD CONSTRAINT `badmintok_notice_author_id_e0d92273_fk_accounts_user_id` FOREIGN KEY (`author_id`) REFERENCES `accounts_user` (`id`);
CREATE INDEX `badmintok_n_is_pinn_5166ff_idx` ON `badmintok_notice` (`is_pinned` DESC, `created_at` DESC);
CREATE INDEX `badmintok_n_author__fb9a7f_idx` ON `badmintok_notice` (`author_id`);


-- Migration: admin.0001_initial
--
-- Create model LogEntry
--
CREATE TABLE `django_admin_log` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `action_time` datetime(6) NOT NULL, `object_id` longtext NULL, `object_repr` varchar(200) NOT NULL, `action_flag` smallint UNSIGNED NOT NULL CHECK (`action_flag` >= 0), `change_message` longtext NOT NULL, `content_type_id` integer NULL, `user_id` bigint NOT NULL);
ALTER TABLE `django_admin_log` ADD CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`);
ALTER TABLE `django_admin_log` ADD CONSTRAINT `django_admin_log_user_id_c564eba6_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`);


-- Migration: admin.0002_logentry_remove_auto_add
--
-- Alter field action_time on logentry
--
-- (no-op)


-- Migration: admin.0003_logentry_add_action_flag_choices
--
-- Alter field action_flag on logentry
--
-- (no-op)


-- Migration: auth.0001_initial
--
-- Create model Permission
--
CREATE TABLE `auth_permission` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `name` varchar(50) NOT NULL, `content_type_id` integer NOT NULL, `codename` varchar(100) NOT NULL);
--
-- Create model Group
--
CREATE TABLE `auth_group` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `name` varchar(80) NOT NULL UNIQUE);
CREATE TABLE `auth_group_permissions` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `group_id` integer NOT NULL, `permission_id` integer NOT NULL);
--
-- Create model User
--
-- (no-op)
ALTER TABLE `auth_permission` ADD CONSTRAINT `auth_permission_content_type_id_codename_01ab375a_uniq` UNIQUE (`content_type_id`, `codename`);
ALTER TABLE `auth_permission` ADD CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`);
ALTER TABLE `auth_group_permissions` ADD CONSTRAINT `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` UNIQUE (`group_id`, `permission_id`);
ALTER TABLE `auth_group_permissions` ADD CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`);
ALTER TABLE `auth_group_permissions` ADD CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`);


-- Migration: auth.0002_alter_permission_name_max_length
--
-- Alter field name on permission
--
ALTER TABLE `auth_permission` MODIFY `name` varchar(255) NOT NULL;


-- Migration: auth.0003_alter_user_email_max_length
--
-- Alter field email on user
--
-- (no-op)


-- Migration: auth.0004_alter_user_username_opts
--
-- Alter field username on user
--
-- (no-op)


-- Migration: auth.0005_alter_user_last_login_null
--
-- Alter field last_login on user
--
-- (no-op)


-- Migration: auth.0007_alter_validators_add_error_messages
--
-- Alter field username on user
--
-- (no-op)


-- Migration: auth.0008_alter_user_username_max_length
--
-- Alter field username on user
--
-- (no-op)


-- Migration: auth.0009_alter_user_last_name_max_length
--
-- Alter field last_name on user
--
-- (no-op)


-- Migration: auth.0010_alter_group_name_max_length
--
-- Alter field name on group
--
ALTER TABLE `auth_group` MODIFY `name` varchar(150) NOT NULL;


-- Migration: auth.0011_update_proxy_permissions
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL


-- Migration: auth.0012_alter_user_first_name_max_length
--
-- Alter field first_name on user
--
-- (no-op)


-- Migration: contenttypes.0001_initial
--
-- Create model ContentType
--
CREATE TABLE `django_content_type` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `name` varchar(100) NOT NULL, `app_label` varchar(100) NOT NULL, `model` varchar(100) NOT NULL);
--
-- Alter unique_together for contenttype (1 constraint(s))
--
ALTER TABLE `django_content_type` ADD CONSTRAINT `django_content_type_app_label_model_76bd3d3b_uniq` UNIQUE (`app_label`, `model`);


-- Migration: contenttypes.0002_remove_content_type_name
--
-- Change Meta options on contenttype
--
-- (no-op)
--
-- Alter field name on contenttype
--
ALTER TABLE `django_content_type` MODIFY `name` varchar(100) NULL;
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
--
-- Remove field name from contenttype
--
ALTER TABLE `django_content_type` DROP COLUMN `name`;


-- Migration: sessions.0001_initial
--
-- Create model Session
--
CREATE TABLE `django_session` (`session_key` varchar(40) NOT NULL PRIMARY KEY, `session_data` longtext NOT NULL, `expire_date` datetime(6) NOT NULL);
CREATE INDEX `django_session_expire_date_a5c62663` ON `django_session` (`expire_date`);

