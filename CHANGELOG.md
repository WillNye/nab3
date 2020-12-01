# Change Log

---

# 0.2.0 (2020/12/01)

## Notes
* Created an `Exclude` class. It is the negation of the `Filter` class, providing a mechanism to remove objects based on given parameters.

---

# 0.1.7 (2020/11/19)

## Notes
* Added additional filter options
    * `startswith`
    * `startswith_any`
    * `endswith`
    * `endswith_any`

---

# 0.1.6 (2020/10/14)

## Notes
* Updated Service.load methods to include force param
* Cleaned up Passing force to Service.load methods
* Updated ServiceWrapper.__setattr__ to properly set service attributes
* Fix issue when calling a ServiceWrapper.service.list if the service had already been loaded
* Fix issue where ServiceWrapper wasn't passing the load param to the Service class

---

# 0.1.5 (2020/10/14)

## Notes
* ServiceWrapper.is_list now public instead of protected
* Fixed Filter._match behavior on nested service lookups 
* Iterating a list of Service objects now properly yielding with the ServiceWrapper 
* Created an account property within the ClientHandler to return the account id for the current session
* Added the EC2 Image service


---

# 0.1.4 (2020/10/06)

## Notes
* Standardizing response on a list of dicts that hit on a service
* Optional force argument to manually reload an object and related attrs e.g. `asg_resp.fetch('security_groups', force=True)`

---

# 0.1.2 (2020/09/30)

## Notes
* No longer fetching instances when calling ASG.fetch('pricing')
* Fix bad response from the Pricing.load_pricing when pricing is already loaded
* Remove default None in getattr within Filter._match

---

# 0.1.1 (2020/09/28)

## Notes
* Cleaned up README
* Added an interval argument to `set_service_stats` and `set_n_service_stats`
* Added support for `ECSCluster.security_groups`
* Created a `PricingMixin`
* Pricing support added to:
  * `EC2Instance` 
  * `ASG` 
  * `ECSCluster` 

---

# 0.1.0 (2020/09/22)

## Notes
* Initial Release
