# TCL Test Example 3: Complex nested structures
# Expected: 2 procs with high complexity

proc validate_and_process {data threshold} {
    # CC = 7 (base + foreach + 2*if + 2*elseif + logical ||)
    set valid_items [list]
    set invalid_items [list]
    
    foreach item $data {
        # First validation
        if {$item eq "" || [string length $item] == 0} {
            lappend invalid_items $item
            continue
        }
        
        # Check threshold
        if {$item > $threshold} {
            # Further classification
            if {$item % 3 == 0} {
                lappend valid_items "divisible_by_3:$item"
            } elseif {$item % 2 == 0} {
                lappend valid_items "even:$item"
            } else {
                lappend valid_items "odd:$item"
            }
        }
    }
    
    return [list $valid_items $invalid_items]
}

proc calculate_score {value type} {
    # CC = 5 (base + switch counts as multiple paths)
    set score 0
    
    switch -exact $type {
        "high" {
            set score [expr {$value * 3}]
        }
        "medium" {
            set score [expr {$value * 2}]
        }
        "low" {
            set score $value
        }
        default {
            set score 0
        }
    }
    
    # Additional check
    if {$score > 100} {
        set score 100
    }
    
    return $score
}

# Test calls
validate_and_process {10 20 30 40} 15
calculate_score 45 "high"
