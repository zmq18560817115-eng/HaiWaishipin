-- TikTok 竞品库（Phase 1）

CREATE TABLE IF NOT EXISTS raw_links (
  link_id       INT PRIMARY KEY,
  url           VARCHAR(512) NOT NULL,
  category      VARCHAR(64)  NOT NULL DEFAULT 'breast_pump',
  platform      VARCHAR(32)  NOT NULL DEFAULT 'tiktok',
  subcategory   VARCHAR(64)  NULL,
  source        VARCHAR(32)  NOT NULL DEFAULT 'manual',
  status        ENUM('pending','fetched','decomposed','archived') NOT NULL DEFAULT 'pending',
  notes         TEXT NULL,
  added_at      DATE NULL,
  UNIQUE KEY uk_url (url(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS videos_meta (
  link_id         INT PRIMARY KEY,
  url             VARCHAR(512) NOT NULL,
  video_id        VARCHAR(64)  NULL,
  author          VARCHAR(128) NULL,
  title           TEXT NULL,
  description     TEXT NULL,
  hashtags        JSON NULL,
  thumbnail_url   VARCHAR(1024) NULL,
  fetched_at      DATETIME NULL,
  fetch_status    VARCHAR(32) NOT NULL DEFAULT 'pending',
  fetch_provider  VARCHAR(32) NULL,
  error_message   TEXT NULL,
  FOREIGN KEY (link_id) REFERENCES raw_links(link_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS video_analysis (
  link_id            INT PRIMARY KEY,
  url                VARCHAR(512) NOT NULL,
  video_id           VARCHAR(64)  NULL,
  author             VARCHAR(128) NULL,
  hook_3s            TEXT NULL COMMENT '前3秒钩子',
  pain_points        TEXT NULL COMMENT '痛点',
  selling_points     TEXT NULL COMMENT '卖点',
  scenes             TEXT NULL COMMENT '场景',
  video_structure    TEXT NULL COMMENT '视频结构',
  subtitle_layout    TEXT NULL COMMENT '字幕排布',
  cta                TEXT NULL COMMENT 'CTA',
  reusable_template  TEXT NULL COMMENT '可复用模板',
  analyzed_at        DATETIME NULL,
  analyze_status     VARCHAR(32) NOT NULL DEFAULT 'pending',
  analyze_provider   VARCHAR(32) NULL,
  error_message      TEXT NULL,
  FOREIGN KEY (link_id) REFERENCES raw_links(link_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS script_templates (
  template_id      VARCHAR(64) PRIMARY KEY,
  label            VARCHAR(128) NOT NULL,
  structure_chain  VARCHAR(512) NOT NULL,
  video_count      INT NOT NULL DEFAULT 0,
  sample_link_ids  VARCHAR(256) NULL,
  suitable_for     VARCHAR(256) NULL,
  notes            TEXT NULL,
  updated_at       DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS product_materials (
  product_id          VARCHAR(64) PRIMARY KEY,
  product_name        VARCHAR(256) NOT NULL,
  target_audience     TEXT NULL,
  core_selling_points TEXT NULL,
  pain_points         TEXT NULL,
  usage_scenarios     TEXT NULL,
  forbidden_terms     TEXT NULL,
  price_range         VARCHAR(128) NULL,
  competitor_ref      TEXT NULL,
  source_path         VARCHAR(1024) NULL,
  synced_at           DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS product_materials (
  product_id         VARCHAR(64) PRIMARY KEY,
  product_name       VARCHAR(256) NOT NULL,
  target_audience    TEXT NULL,
  core_selling_points TEXT NULL,
  pain_points        TEXT NULL,
  usage_scenarios    TEXT NULL,
  forbidden_terms    TEXT NULL,
  price_range        VARCHAR(128) NULL,
  competitor_ref     TEXT NULL,
  source_path        VARCHAR(1024) NULL,
  synced_at          DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
