# TCL Flat Code Examples (No Functions/Procs)
# These examples test basic complexity calculation without function definitions

# Example 1: Simple variable assignments (CC = 1)
set x 10
set y 20
set z [expr {$x + $y}]

# Example 2: Single if statement (CC = 2)
if {$x > 5} {
    puts "x is greater than 5"
}

# Example 3: If-else statement (CC = 2)
if {$x > 10} {
    puts "x is greater than 10"
} else {
    puts "x is not greater than 10"
}

# Example 4: If-elseif-else chain (CC = 4)
if {$x < 5} {
    puts "x is less than 5"
} elseif {$x < 10} {
    puts "x is less than 10"
} elseif {$x < 15} {
    puts "x is less than 15"
} else {
    puts "x is 15 or greater"
}

# Example 5: While loop (CC = 2)
set counter 0
while {$counter < 10} {
    puts "Counter: $counter"
    incr counter
}

# Example 6: For loop (CC = 2)
for {set i 0} {$i < 10} {incr i} {
    puts "Iteration: $i"
}

# Example 7: Foreach loop (CC = 2)
set mylist {apple banana cherry}
foreach item $mylist {
    puts "Item: $item"
}

# Example 8: Nested if statements (CC = 4)
if {$x > 5} {
    if {$y > 15} {
        puts "Both conditions met"
    }
}

# Example 9: Switch statement (CC = 5 - one per case pattern)
switch $x {
    1 {
        puts "One"
    }
    2 {
        puts "Two"
    }
    3 {
        puts "Three"
    }
    default {
        puts "Other"
    }
}

# Example 10: Logical operators (CC = 3)
if {$x > 5 && $y < 30} {
    puts "Compound condition met"
}

if {$x < 0 || $y < 0} {
    puts "At least one is negative"
}

# Example 11: Complex nested structure (CC = 7)
if {$x > 0} {
    while {$x < 100} {
        if {$x % 2 == 0} {
            puts "Even: $x"
        } elseif {$x % 3 == 0} {
            puts "Divisible by 3: $x"
        }
        incr x
    }
}

# Example 12: Try-catch error handling (CC = 2)
if {[catch {
    set result [expr {10 / 0}]
} error_msg]} {
    puts "Error occurred: $error_msg"
}

# Example 13: Inline brace style
if {$x > 0} { puts "Positive" } else { puts "Non-positive" }

# Example 14: Multiple conditions with and/or
if {$x > 5 && $y > 10 || $z > 15} {
    puts "Complex condition satisfied"
}

# Example 15: Foreach with nested if
foreach num {1 2 3 4 5 6 7 8 9 10} {
    if {$num % 2 == 0} {
        puts "$num is even"
    }
}
