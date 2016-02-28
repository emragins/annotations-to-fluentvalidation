# annotations-to-fluentvalidation
Script to convert a project from using DataAnnotations to Jeremy Skinner's FluentValidation library

This will transform common DataAnnotations into Rules on an AbstractValidator class which will be placed 
directly below the original class in the same file.

It will remove tags which it feels are safely "irrelevant".  

`DataType(...)` attributes are left in place to allow `Html.InputFor(...)` items to render the input type correctly.

Scenarios that the script does not know how to handle will be either reported as "UnresolvedTag" or with an "Error" (you'll get a build error in either case).

Known limitations:
* All `DataType` tags are not handled
* Specifically typed tags are not handled (ex. `Password`, `EmailAddress`)
* Custom validations are not handled
* Less common validations are not handled


## Requirements
Python 3 as a command line utility

## Usage
Execute the script and pass in the the directory
` python .\main.py "C:\myproject\src" `

** Don't forget to make a back-up of your code before running this script.  
I recommend just making a fresh commit so that it's easy to see what's changed
and to rollback if you don't like the results.

### Customization
The script is fairly opinionated.  There are a couple arrays that would be easy to modify it's behavior, however.
* `excludeAnnotations`:  List of annotations to completely ignore
* `excludeTagsFromDeletion`:  List of tags NOT to delete from the original class.
* `excludeDirs`:  List of directory names to ignore
* `excludeFiles`: File names which contain anything in this list will be ignored.  Does not currently support pattern matching. 


### Example 1

#### Input
``` csharp
using System;
using System.ComponentModel.DataAnnotations;
//...

namespace MyProject
{
    [AuthorizePermissions(PermissionObjects.Trip, AppActions.Create)]
    public class UpdateScheduleCommand : CommandBase
    {
        public int TripId { get; set; }

        [Range(1, int.MaxValue, ErrorMessage = "Origin must be provided.")]
        public int OriginId { get; set; }
        [Range(1, int.MaxValue, ErrorMessage = "Destination must be provided.")]
        public int DestinationId { get; set; }

        [Required(ErrorMessage = "StartDate must be provided.")]
        public DateTime? StartDate { get; set; }
        [Required(ErrorMessage = "ReturnDate must be provided.")]
        public DateTime? ReturnDate { get; set; }

        public TripDirections TripDirection { get; set; }
        [CustomValidation(typeof(UpdateScheduleCommand), "ValidateToTimes")]
        public BusTimes ToSegBusTimes { get; set; }
        [CustomValidation(typeof(UpdateScheduleCommand), "ValidateFromTimes")]
        public BusTimes FromSegBusTimes { get; set; }

        // ... Custom Validation methods
    }
}
```

#### Output
``` csharp
using FluentValidation; 
using System;
using System.ComponentModel.DataAnnotations;
// ...

namespace MyProject
{
    [AuthorizePermissions(PermissionObjects.Trip, AppActions.Create)]
    public class UpdateScheduleCommand : CommandBase
    {
        public int TripId { get; set; }

        public int OriginId { get; set; }
        public int DestinationId { get; set; }

        public DateTime? StartDate { get; set; }
        public DateTime? ReturnDate { get; set; }

        public TripDirections TripDirection { get; set; }
        public BusTimes ToSegBusTimes { get; set; }
        public BusTimes FromSegBusTimes { get; set; }

        // ... Custom Validation methods remain in place
    }
    public class UpdateScheduleCommandValidator : AbstractValidator<UpdateScheduleCommand>
    {
        public UpdateScheduleCommandValidator()
        {
            RuleFor(x => x.OriginId).Length(1, int.MaxValue).WithMessage("Origin must be provided.");
            RuleFor(x => x.DestinationId).Length(1, int.MaxValue).WithMessage("Destination must be provided.");
            RuleFor(x => x.StartDate).NotEmpty().WithMessage("StartDate must be provided.");
            RuleFor(x => x.ReturnDate).NotEmpty().WithMessage("ReturnDate must be provided.");
            RuleFor(x => x.ToSegBusTimes).UnresolvedTag(Annotation: CustomValidation, Values: None, Message: None);
            RuleFor(x => x.FromSegBusTimes).UnresolvedTag(Annotation: CustomValidation, Values: None, Message: None);
        }
    }
    
}
```

### Example 2

#### Input
``` csharp
public class ResetPasswordViewModel
{
    [Required]
    [EmailAddress]
    [Display(Name = "Email")]
    public string Email { get; set; }

    [Required]
    [StringLength(100, ErrorMessage = "The {0} must be at least {2} characters long.", MinimumLength = 6)]
    [DataType(DataType.Password)]
    [Display(Name = "Password")]
    public string Password { get; set; }

    [DataType(DataType.Password)]
    [Display(Name = "Confirm password")]
    [Compare("Password", ErrorMessage = "The password and confirmation password do not match.")]
    public string ConfirmPassword { get; set; }

    public string Code { get; set; }
}
```

### Output 
``` csharp
public class ResetPasswordViewModel
{
    [EmailAddress]
    [Display(Name = "Email")]
    public string Email { get; set; }

    [DataType(DataType.Password)]
    [Display(Name = "Password")]
    public string Password { get; set; }

    [DataType(DataType.Password)]
    [Display(Name = "Confirm password")]
    public string ConfirmPassword { get; set; }

    public string Code { get; set; }
}

public class ResetPasswordViewModelValidator : AbstractValidator<ResetPasswordViewModel>
{
    public ResetPasswordViewModelValidator()
    {
        RuleFor(x => x.Email).NotEmpty();
        RuleFor(x => x.Email).UnresolvedTag(Annotation: EmailAddress, Values: None, Message: None);
        RuleFor(x => x.Password).NotEmpty();
        RuleFor(x => x.Password).Length(100, Int32.MaxValue).WithMessage("The {0} must be at least {2} characters long.", MinimumLength = ");
        RuleFor(x => x.Password).UnresolvedTag(Annotation: DataType, Values: DataType.Password, Message: None);
        RuleFor(x => x.ConfirmPassword).UnresolvedTag(Annotation: DataType, Values: DataType.Password, Message: None);
        RuleFor(x => x.ConfirmPassword).UnresolvedTag(Annotation: Compare, Values: None, Message: The password and confirmation password do not match.).WithMessage("The password and confirmation password do not match.");
    }
}
```

## Contributing
Please feel free to extend and modify this code.  I'm happy to merge in pull requests.

This project is licensed under GNU General Public License v3.0.  