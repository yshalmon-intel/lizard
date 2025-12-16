# TCL Test Example 2: Loops and iterations
# Expected: 3 procs with varying complexity

proc count_up {max} {
    # CC = 2 (base + for)
    for {set i 0} {$i < $max} {incr i} {
        puts "Count: $i"
    }
}

proc process_list {items} {
    # CC = 4 (base + foreach + if + logical &&)
    set result [list]
    foreach item $items {
        if {$item > 0 && $item < 100} {
            lappend result $item
        }
    }
    return $result
}

proc iterate_while {start limit} {
    # CC = 3 (base + while + if)
    set current $start
    while {$current < $limit} {
        if {$current % 2 == 0} {
            puts "Even: $current"
        }
        incr current
    }
}

# Test calls
count_up 5
process_list {10 20 150 50}
iterate_while 0 10
