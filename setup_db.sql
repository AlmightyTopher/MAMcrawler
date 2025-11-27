CREATE DATABASE audiobook_automation;
CREATE USER audiobook_user WITH PASSWORD 'audiobook_password';
GRANT ALL PRIVILEGES ON DATABASE audiobook_automation TO audiobook_user;
ALTER DATABASE audiobook_automation OWNER TO audiobook_user;
