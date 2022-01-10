# Change Log

## [0.2.1] - 2022-01-10
### Fixed
* If an object that is to be added to a table, which contains as a attribute a list with further BaseModels that have a special insert, an error occurred. This has now been fixed  by @Phil997 in #7

 
## [0.2.0] - 2022-01-10
### Added
* Add support for 'Literal, List, Any, Optional, Union' and List[BaseModels] by @Phil997 in https://github.com/Phil997/pydantic-sqlite/pull/4
* GitHub Action for tests on a pull Request by @Phil997 in https://github.com/Phil997/pydantic-sqlite/pull/6
### Changed
* Update nested models per default, whan adding a obj with nested BaseModels by @Phil997 in https://github.com/Phil997/pydantic-sqlite/pull/3
* Revise the save logic by @Phil997 in https://github.com/Phil997/pydantic-sqlite/pull/5
### Fixed
* Fix Error that attributes of an object, which are nested BaseModels, are changed when adding it to the database. by @Phil997 in https://github.com/Phil997/pydantic-sqlite/pull/3


## [0.1.1] - 2021-12-30
### Fixed
* Fix Error Messages with wrong foreign keys in DataBase.add
