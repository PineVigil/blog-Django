-- ============================================================
-- toflower blog · MySQL 8.0 初始化脚本
-- 用法:mysql -u root -p < deploy/mysql_init.sql
-- ============================================================

-- 创建数据库(utf8mb4 支持完整 Unicode,含 emoji)
CREATE DATABASE IF NOT EXISTS toflower_blog
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

-- 创建专用用户(密码请修改!)
CREATE USER IF NOT EXISTS 'toflower'@'localhost' IDENTIFIED BY 'change-this-strong-password';
CREATE USER IF NOT EXISTS 'toflower'@'127.0.0.1'   IDENTIFIED BY 'change-this-strong-password';

-- 授权
GRANT ALL PRIVILEGES ON toflower_blog.* TO 'toflower'@'localhost';
GRANT ALL PRIVILEGES ON toflower_blog.* TO 'toflower'@'127.0.0.1';

-- 刷新权限
FLUSH PRIVILEGES;

-- 验证
SELECT User, Host FROM mysql.user WHERE User = 'toflower';
SHOW CREATE DATABASE toflower_blog;
