# TCL Test Example 1: Simple procedure with basic control flow
# Expected: 1 proc, CC=3 (base + if + elseif)

proc check_value {val} {
    if {$val < 0} {
        puts "Negative"
        return -1
    } elseif {$val == 0} {
        puts "Zero"
        return 0
    } else {
        puts "Positive"
        return 1
    }
}

# Test it
check_value 5
check_value -3
check_value 0
