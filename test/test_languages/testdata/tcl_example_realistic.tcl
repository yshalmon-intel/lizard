# TCL Test Example 5: Real-world-like procedures
# Expected: Realistic TCL code patterns from EDA tools

proc parse_timing_constraint {sdc_line} {
    # CC = 6 (base + switch patterns + if)
    set cmd [lindex $sdc_line 0]
    
    switch -glob $cmd {
        "create_clock" {
            set period [lindex $sdc_line 2]
            puts "Clock period: $period"
        }
        "set_input_delay" {
            set delay [lindex $sdc_line 1]
            set port [lindex $sdc_line 3]
            puts "Input delay $delay on $port"
        }
        "set_output_delay" {
            set delay [lindex $sdc_line 1]
            set port [lindex $sdc_line 3]
            puts "Output delay $delay on $port"
        }
        default {
            puts "Unknown constraint: $cmd"
        }
    }
    
    if {[llength $sdc_line] > 5} {
        puts "Warning: Long constraint line"
    }
}

proc filter_cells_by_type {cell_list type_pattern} {
    # CC = 5 (base + foreach + if + 2*logical operators)
    set matched_cells [list]
    
    foreach cell $cell_list {
        set cell_type [get_attribute $cell ref_name]
        
        if {[string match $type_pattern $cell_type] && $cell ne ""} {
            if {[get_attribute $cell is_hierarchical] || [get_attribute $cell is_sequential]} {
                lappend matched_cells $cell
            }
        }
    }
    
    return $matched_cells
}

proc report_statistics {design} {
    # CC = 8 (base + 3*foreach + 4*if)
    set total_cells 0
    set sequential_count 0
    set combinational_count 0
    
    foreach cell [get_cells -hier] {
        incr total_cells
        
        if {[get_attribute $cell is_sequential]} {
            incr sequential_count
        } else {
            incr combinational_count
        }
        
        # Check for high fanout
        set fanout [sizeof_collection [all_fanout -from $cell]]
        if {$fanout > 100} {
            puts "High fanout cell: $cell (fanout: $fanout)"
        }
    }
    
    # Report nets
    foreach net [get_nets -hier] {
        set driver [get_pins -of $net -filter "direction==out"]
        if {$driver eq ""} {
            puts "Warning: Net $net has no driver"
        }
    }
    
    # Report ports  
    foreach port [get_ports] {
        if {[get_attribute $port direction] eq "in"} {
            # Check input delay
            if {![info exists input_delay($port)]} {
                puts "Warning: No input delay on $port"
            }
        }
    }
    
    puts "Total cells: $total_cells"
    puts "Sequential: $sequential_count"
    puts "Combinational: $combinational_count"
}

# Test calls
parse_timing_constraint {create_clock -period 10 clk}
filter_cells_by_type {cell1 cell2 cell3} "INV*"
report_statistics "my_design"
