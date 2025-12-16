# TCL Test Example 4: Error handling and special cases
# Expected: 3 procs demonstrating error handling patterns

proc safe_divide {numerator denominator} {
    # CC = 2 (base + if with catch)
    if {[catch {expr {$numerator / $denominator}} result]} {
        puts "Error: Division failed - $result"
        return 0
    }
    return $result
}

proc read_file_safe {filename} {
    # CC = 4 (base + if + if + logical &&)
    if {[catch {open $filename r} fileHandle]} {
        puts "Error: Cannot open file $filename"
        return ""
    }
    
    set content ""
    if {[catch {read $fileHandle} data]} {
        puts "Error: Cannot read file"
    } else {
        set content $data
    }
    
    catch {close $fileHandle}
    return $content
}

proc process_with_defaults {value {multiplier 1} {offset 0}} {
    # CC = 3 (base + if + elseif) - Testing default parameters
    set result [expr {$value * $multiplier + $offset}]
    
    if {$result < 0} {
        return 0
    } elseif {$result > 1000} {
        return 1000
    } else {
        return $result
    }
}

# Test calls
safe_divide 10 2
safe_divide 10 0
read_file_safe "/nonexistent/file.txt"
process_with_defaults 50
process_with_defaults 50 2
process_with_defaults 50 2 100
