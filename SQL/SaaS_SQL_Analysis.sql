create database saas;

use saas;

create table customers(Customer_Id varchar(20) primary key ,Signup_Date date,Country varchar(20),Industry varchar(20),Company_Size varchar(20),Segment varchar(20));
desc customers;

create table plans(Plan_Id varchar(20) primary key,Plan_Name varchar(20), Monthly_Price decimal(5,2),Billing_Cycle varchar(20));
desc plans;

create table subscriptions(Subscription_Id varchar(20) primary key,Customer_Id varchar(20) not null,Plan_Id varchar(20) not null,Start_Date date,End_Date varchar(20) null,
Status varchar(20),Subscription_Days decimal(6,2) null,
constraint fk_customerid foreign key (Customer_Id) references customers(Customer_Id),
constraint fk_planid foreign key (Plan_Id) references plans(Plan_Id));
desc subscriptions;


create table payments(Payment_Id varchar(20) primary key,Subscription_Id varchar(20) not null,Payment_Date date ,Amount decimal(6,2),
Payment_Status varchar(15),Payment_Method varchar(15),
constraint fk_subscriptionid foreign key (Subscription_Id) references subscriptions(Subscription_Id));
desc payments;

create table feat_usage(Usage_Id varchar(20) primary key,Customer_Id varchar(20) not null,Event_Date date null,
Feature_Name varchar(20),Login_Count int,Session_Minutes decimal(8,2),
constraint fk_usagecustomerid foreign key (Customer_Id) references customers(Customer_Id));
desc feat_usage;

create table support(Ticket_Id varchar(20) primary key,Customer_Id varchar(20) not null,Ticket_Date date,Priority varchar(15),Category varchar(20),
Resolution_Time int, Status varchar(20),constraint fk_supportcustomerid foreign key (Customer_Id) references customers(Customer_Id));
desc support;

desc subscriptions;

select * from customers limit 10;
select * from plans;
select * from subscriptions limit 10;
select * from payments limit 10;
select * from feat_usage limit 10;
select * from support limit 10;

select count(*) from customers;
select count(*) from plans;
select count(*) from subscriptions;
select count(*) from payments;
select count(*) from feat_usage;
select count(*) from support;

#Revenue by Plan
select p.Plan_Name,sum(pay.Amount) as total_revenue from payments as pay join subscriptions as sub on pay.Subscription_Id=sub.Subscription_Id 
join plans as p on sub.Plan_Id=p.Plan_Id where pay.Payment_Status="Paid" group by p.Plan_Name order by total_revenue desc;

#Revenue by Country
select c.Country,sum(p.Amount) as total_revenue from payments as p join subscriptions as sub on p.Subscription_Id=sub.Subscription_ID 
join customers as c on c.Customer_Id=sub.Customer_Id where p.Payment_Status="Paid" group by c.Country order by total_revenue;

#Revenue by Industry
select c.Industry,sum(p.Amount) as total_revenue from payments as p join subscriptions as sub on p.Subscription_Id=sub.Subscription_ID 
join customers as c on c.Customer_Id=sub.Customer_Id where p.Payment_Status="Paid" group by c.Industry order by total_revenue;

#Revenue by Customer Segment
select c.Segment,sum(p.Amount) as total_revenue from payments as p join subscriptions as sub on p.Subscription_Id=sub.Subscription_ID 
join customers as c on c.Customer_Id=sub.Customer_Id where p.Payment_Status="Paid" group by c.Segment order by total_revenue;

#Churn Rate by Plan
select p.Plan_Name,count(*) as total_subscriptions,
sum(case when sub.Status='Churned' then 1 else 0 end) as churned,round(sum(case when sub.Status="Churned" then 1 else 0 end) * 100.0 / count(*),2) as churnrate
from subscriptions as sub join plans as p on sub.Plan_Id= p.Plan_Id group by p.Plan_Name;


#Churn Rate by Country
select c.Country,count(*) as totalsubscriptions,sum(case when sub.Status="Churned" then 1 else 0 end) as churned,
round(sum(case when sub.Status="Churned" then 1 else 0 end)*100.0 /count(*),2) as churnrate
from subscriptions as sub join customers as c on sub.Customer_Id=c.Customer_Id group by c.Country order by churnrate desc;

#Feature usage by Plan
select p.Plan_Name,u.Feature_Name ,count(*) as usage_count from feat_usage as u join subscriptions as sub on u.Customer_Id = sub.Customer_Id 
join plans as p on p.Plan_Id = sub.Plan_Id group by p.Plan_Name,u.Feature_Name;

#Support Tickets by Industry
select c.Industry,count(*) as total_tickets from support as s join customers as c 
on s.Customer_Id=c.Customer_Id group by c.Industry order by total_tickets desc ;

#Top 10 Customers by Revenue
select c.Customer_ID,c.Country,c.Segment,sum(p.Amount) as revenue from payments as p join 
subscriptions as sub on p.Subscription_Id=sub.Subscription_Id join customers as c on c.Customer_ID =sub.Customer_Id
where p.Payment_Status="Paid" group by c.Customer_Id,c.Country,c.Segment order by revenue desc limit 10 ;

#Monthly Revenue by Plan
select date_format(pay.Payment_Date,"%Y-%m") as month,p.Plan_Name,sum(pay.Amount) as total_Revenue from payments as pay
join subscriptions as sub on pay.Subscription_Id=sub.Subscription_Id join plans as p on sub.Plan_Id=p.Plan_Id 
where pay.Payment_Status="Paid" group by date_format(pay.Payment_Date,"%Y-%m"),p.Plan_Name order by month,p.Plan_Name;

#CTE
#Customers Above Average Revenue
with customer_revenue as (
select c.Customer_ID,sum(pay.Amount) as total_revenue from payments as pay join subscriptions as s 
on pay.Subscription_Id=s.Subscription_Id join customers as c on c.Customer_Id=s.Customer_Id 
where pay.Payment_status="Paid"
group by c.Customer_Id )
select * from customer_revenue where total_revenue>(select avg(total_revenue) from customer_revenue
) 
order by total_revenue desc;

#Customers with Multiple Subscriptions
with customer_subscriptions as (
select Customer_Id,count(Subscription_Id) as total_subscriptions from subscriptions group by Customer_Id
)
select * from customer_subscriptions where total_subscriptions >1 order by total_subscriptions desc;

#Plans with Highest Churn
with churnedcustomers as (
select Plan_Name,count(*) as churncustomers from subscriptions as sub join plans as p on sub.Plan_Id = p.Plan_Id 
where sub.Status="Churned" group by p.Plan_Name
)
select * from churnedcustomers order by churncustomers desc;

#Countries with Highest Revenue
with highrevenue as (
select c.Country,sum(p.Amount) as totalrevenue from payments as p join subscriptions as sub 
on p.Subscription_Id=sub.Subscription_Id join customers as c on c.Customer_Id=sub.Customer_Id 
where p.Payment_Status='Paid' group by c.Country
)
select * from highrevenue order by totalrevenue desc;

#Windows Function
#Top 10 Customers by Revenue using RANK()

with customerrevenue as (
select c.Customer_Id,sum(pay.Amount) as totalrevenue from payments as pay join subscriptions as s on pay.Subscription_Id = s.Subscription_Id join customers as c 
on c.Customer_Id=s.Customer_Id where pay.Payment_Status='Paid' group by c.Customer_Id
)

select Customer_Id,totalrevenue, rank() over(order by totalrevenue desc) as revenue_rank from customerrevenue limit 10;


#Revenue Running Total
with monthrevenuetotal as (
select date_format(Payment_Date,"%Y-%m") as month,sum(Amount) as totalamount from payments where Payment_Status='Paid' group by month
) 
select month,totalamount,sum(totalamount) over (order by month) as runningtotal from monthrevenuetotal;

#Monthly Revenue Growth 
with revenuegrowth as(
select date_format(Payment_Date,"%Y-%m") as month,sum(Amount) as totalrevenue from payments where Payment_Status="Paid" group by month
)
select month,totalrevenue,lag(totalrevenue) over(order by month) as prevmonth,
totalrevenue-lag(totalrevenue) over (order by month) as growth from revenuegrowth;


#Rank Plans by Monthly Revenue
with plansmonthrevenue as (
select date_format(pay.Payment_Date,"%Y-%m") as month ,p.Plan_Name,sum(pay.Amount) as totalrevenue from payments as pay join subscriptions as s 
on pay.Subscription_Id=s.Subscription_Id join plans as p on s.Plan_Id=p.Plan_Id where pay.Payment_Status='Paid' 
group by month,p.Plan_Name
)
select month,Plan_Name,totalrevenue,rank() over(partition by month order by totalrevenue desc) as monthly_rank from plansmonthrevenue;

#Customer Lifetime Revenue Ranking
with lifetimerevenue as (
select c.Customer_Id,sum(Amount) as totalrevenue from payments as pay join subscriptions as sub on pay.Subscription_Id=sub.Subscription_Id
join customers as c on sub.Customer_Id=c.Customer_Id where pay.Payment_Status="Paid" group by c.Customer_Id
) 
select Customer_ID,totalrevenue ,dense_rank() over(order by totalrevenue desc) as customer_rank from lifetimerevenue;

select * from customers limit 10;
select * from plans;
select * from subscriptions limit 10;
select * from payments limit 10;
select * from feat_usage limit 10;
select * from support limit 10;



