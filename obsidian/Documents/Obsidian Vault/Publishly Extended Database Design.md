1. Products
2. Users
3. Credits
4. Whitelabel

# 1. Products
Products will be the starting point of a users flow in the application. A user can purchase a product from any platform and then be registered in the application. After a successful registration users will get an email with their temporary login details. 
**There can be 3 types of products.**
- [[#Generic Products]]
- [[#Whitelabel Products]]
- [[#Under Whitelabel Products]]

Of course we must use an enum value to insert this values.
#### Product Type Enum

```php 
enum UserTypeEnum:string{  
	case GENERIC = 'generic';
	case WHITELABEL = 'whitelabel';
	case UNDER_WHITELABEL = 'under whitelabel';
}
```


### Generic Products
This products are created by `admin` only. This are just simple products that are marked as `generic`.
### Whitelabel Products
This products are created by `admin` only. This are just simple products marked as `whtelabel`

### Under Whitelabel Products
This products are created by `whitelabel` users only. It will be marked as `under whitelabel` and the user can only assign the permissions to the product that they have access to. Also they can't add credits to a product more that they have.
#### Products Table
```
products
	- id
	- user_id
	- type
	- credits
	- credit_refill_cycle
	// Other columns
```

# 2. Users
All users have to purchase a product to be registered in the application.After a successful purchase, users will get a email notification with the login details to there panel. From there they can login to the panel using the temporary password and then will be asked to create a new password along with creating a new workspace.
**There are 4 Types of users.**
### a. Generic users
If the user purchase a non-whitelabel package from the main landing page the will be registered as `generic` user
### b. Whitelabel Users
If the user purchase a whitelabel package from the main landing page the will be registered as `whitelabel` user
### c. Under Whitelabel Users
if the user purchases a product that was created by the whitelabel users they will be registered as `under whitelabel` users

### d. Administrators
Application Admins that have control over all other users in the application

So to identify this we must have a `type` column in the `users` table. The value can only be an php enum that consist below types
#### User Type Enum

```php 
enum UserTypeEnum:string{  
	case GENERIC = 'generic';
	case WHITELABEL = 'whitelabel';
	case UNDER_WHITELABEL = 'under whitelabel';
	case ADMIN = 'admin';
}
```


# 3. Credits
Credits are just a simple way to limit users from there actions. Every action in the application would be credit based. For instance credits will be used for
- Creating New Workspace *(Thoughts: It will create the illusion that the credits have been deducted but in reality the will be reserved for any activity in this workspace)*
- Generating an Image using Copilot
- Generating  a post content using AI
- Creating a Product For `under whitelabel` users
- Inviting members to a workspace
### Credit Distribution
Credits can be distributed in many ways. The primary way of credit distribution is through products or packages. There may be offers or compensation credits in the future but we will stick to the primary way of distribution for now.

After a product has been created with the specified credits it gets stored into a `credits` column in the [[#Products Table]] with addition to a `credit_refill_cycle` column that indicates the time in between of credit refills. When a user is registered he will be assigned with this credits in a table named `credits`. If the user purchased multiple products, the `total` credits of the existing record of the user will be updated.
#### Credits Table
```
credits
	- id
	- user_id
	- workspace_id
	- total
	- used
	- refilled_at
```

### Credit Usage
Upon each usage of credits the usage will be stored at a new table named `credit_usages`. And the `used` column for that credit record will be updated accordingly in the `credits` table by counting the usages.
#### Credit Usages Table
```
credit_usages
	- id
	- used_for
	- amount
	- is_reserved
	- reserved_for
	- used_at
```

### Credit Refill
Credit refill is a way of resetting the credits at a certain time so they can be reused after that period. So this can be achieved in two ways. We can simply just decrement the `total` column of the `credits` table & refill the credits in every `credit_refill_cyle` and get rid of the  [[#Credit Usage]] feature all together. Or we can take advantage of the [[#Credit Usage]] feature and don't have to decrement the `total` credits or refill the credits anymore. 

Using the latter approach will be much scale-able as we can track the history of credit usages at any point in the future. We just have to calculate the usage on every `credit_refil_cycle` and update the `used` column accordingly.

# 4. Whitelabel
Whitelabel users will have their domain configuration in a table named `whitelabels`.
There is a optional database configuration so that we can implement a multi-database system at any point.

#### Whitelabel Table
```
whitelabels
	- id
	- user_id
	- domain
	- database(json)
		- database
		- username
		- password
```

### Whitelabel User
1. After a successful purchase the user will be redirected to a page where he/she will be asked to enter his domain name. 
2. In the next step the application will provide the user with a cname record of the main server domain to add it to user's DNS configuration.
3. The domain name will be saved to the `whitelabels` table.
4. Random Database credentials will be generated based on the domain name and a new database will be created in the server. Then the tables will be migrated to new database (If separate database is implemented)
5. User will be prompted to stay tuned for the dns propagation.