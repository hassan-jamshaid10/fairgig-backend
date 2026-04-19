# FairGig Backend Overview

The FairGig backend is the technical engine that runs the FairGig platform. It is designed using a microservice architecture, which means that instead of one giant application, the system is broken down into smaller, specialized services that work together efficiently. 

## The Services

The platform primarily uses two programming languages to power these services: Python and Node.js.

The Python services handle the core, day-to-day features of the platform. The Auth Service manages user logins, passwords, and secure access. The Users Service stores profile information for the different types of people using the platform, such as Workers, Verifiers, and Advocates. The Jobs Service is responsible for managing gig postings and job applications. The Earnings Service tracks the work shifts, calculating gross pay and platform deductions, and securely holding screenshot evidence for verification. Lastly, an Anomaly Service runs in the background to detect suspicious activities and flag unusual or fake shift logs.

The Node.js services handle specialized tasks. The Analytics Service connects to the database to study shift data, finding market trends and average pay rates. The Certificate Service automatically generates proof-of-work certificates for users to use on other platforms. The Grievance Service acts as a helpdesk, securely handling any complaints filed by the workers and tracking the progress of resolving these disputes.

## Database Organization

All platform information is stored in a secure master database. To keep everything organized, the database is strictly divided into specialized sections known as schemas. 

The Identity section holds user details, encrypted passwords, and system roles. The financial data is securely stored in the Earnings section, which holds records of shift hours, pay details, and uploaded pay-slip screenshots. Worker complaints, incident descriptions, and community comments are stored separately in the Grievance section.

To strongly protect user privacy, the database uses a special feature called an "anonymized view". This allows the Analytics Service to analyze geographic shift data and calculate statistics without ever having access to the workers' actual names, phone numbers, or email addresses.

## Running the Platform

Software developers can quickly start the entire system on their own computers using the "uv" package manager for Python, or they can use Docker to instantly spin up the entire pre-configured environment in isolated containers. The system is designed to intelligently switch between an offline local database and the live production cloud database simply by changing an environment setting.
