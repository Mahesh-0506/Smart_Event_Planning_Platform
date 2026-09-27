INSERT INTO users(name,email,role,created_at) VALUES ('Project Organizer','organizer@smartevent.local','Organizer',datetime('now'));
INSERT INTO events(name,date,time,venue,capacity,event_type,status,budget,description,created_at,updated_at) VALUES
('AI Workshop','2026-10-10','10:00','Auditorium',200,'Workshop','Upcoming',50000,'AI and intelligent event operations workshop.',datetime('now'),datetime('now')),
('Python Bootcamp','2026-10-15','09:30','Lab 2',120,'Training','Upcoming',30000,'Hands-on Python bootcamp.',datetime('now'),datetime('now')),
('Annual Technical Summit','2026-11-15','10:00','College Auditorium',300,'Conference','Planning',120000,'Annual technical summit with talks and demonstrations.',datetime('now'),datetime('now'));
INSERT INTO resources(name,category,quantity,available,unit,location,status,created_at) VALUES
('Projector','Equipment',5,5,'units','AV Store','Available',datetime('now')),
('Chairs','Furniture',300,300,'units','Main Store','Available',datetime('now')),
('Sound System','Equipment',2,2,'sets','AV Store','Available',datetime('now')),
('Event Coordinator','Staff',4,4,'people','Admin','Available',datetime('now'));
INSERT INTO attendees(name,email,phone,organization,role,created_at) VALUES
('Ananya Rao','ananya@example.com','9000000001','Tech Club','Attendee',datetime('now')),
('Rahul Kumar','rahul@example.com','9000000002','IEEE Student Branch','Attendee',datetime('now'));
INSERT INTO vendors(company_name,contact_name,email,phone,category,status,contract_value,service,created_at) VALUES
('Grand Catering Services','Meera Sharma','catering@example.com','9000000010','Catering','Active',25000,'Food and refreshments',datetime('now')),
('EventPro AV','Kiran Das','av@example.com','9000000011','AV','Active',18000,'Audio visual support',datetime('now'));
INSERT INTO budgets(event_id,category,amount,notes,created_at) VALUES (1,'Overall',50000,'Seed budget',datetime('now')),(2,'Overall',30000,'Seed budget',datetime('now')),(3,'Overall',120000,'Seed budget',datetime('now'));
INSERT INTO expenses(event_id,category,description,amount,expense_date,approval_status,created_at) VALUES (1,'Catering','Refreshments',12000,date('now'),'Approved',datetime('now')),(1,'AV','Projector and audio support',11000,date('now'),'Approved',datetime('now'));
INSERT INTO allocations(event_id,resource_id,quantity,status,allocated_at) VALUES (1,1,1,'Allocated',datetime('now')),(1,4,1,'Allocated',datetime('now')),(2,2,120,'Allocated',datetime('now'));
INSERT INTO notifications(user_id,type,title,message,is_read,created_at) VALUES (1,'Budget','Budget update','AI Workshop has used ₹23,000 of its tracked budget.',0,datetime('now')),(1,'Resource','Resource allocation','Projector is allocated to AI Workshop.',0,datetime('now'));
INSERT INTO workflows(name,trigger_type,action_type,condition_value,is_active,created_at) VALUES ('Budget threshold alert','Budget','Notify','80%',1,datetime('now')),('Resource conflict check','Resource','Block','Same date',1,datetime('now'));
