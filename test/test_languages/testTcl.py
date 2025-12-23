import unittest
from lizard import analyze_file, FileAnalyzer, get_extensions
from lizard_languages import TclReader
from lizard_ext.lizardoutside import LizardExtension as CountOutsideComplexity


def get_tcl_function_list(source_code):
    """Helper function to analyze TCL source code and return function list."""
    return analyze_file.analyze_source_code(
        "test.tcl", source_code).function_list


def get_tcl_function_list_with_extension(source_code, extension):
    """Helper function to analyze TCL source code with an extension."""
    return FileAnalyzer(get_extensions([extension])).analyze_source_code(
        "test.tcl", source_code).function_list


class TestTclTokenizer(unittest.TestCase):
    """Test TCL tokenization."""

    def check_tokens(self, expect, source):
        """Helper to check if tokenization matches expected tokens."""
        tokens = list(TclReader.generate_tokens(source))
        self.assertEqual(expect, tokens)

    def test_simple_tokens(self):
        """Test basic token splitting."""
        self.check_tokens(['set', ' ', 'x', ' ', '10'], 'set x 10')

    def test_comment(self):
        """Test comment handling."""
        self.check_tokens(['set', ' ', 'x', ' ', '10', ' ', '# comment', '\n'], 
                         'set x 10 # comment\n')

    def test_braced_string(self):
        """Test braced string tokenization."""
        # TCL braces are individual tokens for better parsing
        self.check_tokens(['puts', ' ', '{', 'hello', ' ', 'world', '}'], 'puts {hello world}')

    def test_quoted_string(self):
        """Test quoted string."""
        self.check_tokens(['puts', ' ', '"hello world"'], 'puts "hello world"')

    def test_command_substitution(self):
        """Test command substitution [...]."""
        self.check_tokens(['set', ' ', 'x', ' ', '[expr {1 + 2}]'], 
                         'set x [expr {1 + 2}]')

    def test_variable_substitution(self):
        """Test variable substitution $var."""
        self.check_tokens(['puts', ' ', '$x'], 'puts $x')

    def test_escaped_braces_in_comment(self):
        """Test that escaped braces in comments don't break parsing."""
        # This was causing issues - escaped braces were being treated as structural braces
        self.check_tokens(['# puts $fp "if \\(\\$derived\\_upf\\) \\{"', '\n'], 
                         '# puts $fp "if \\(\\$derived\\_upf\\) \\{"\n')

    def test_escaped_braces_in_string(self):
        """Test escaped braces in quoted strings."""
        self.check_tokens(['puts', ' ', '"test \\{ and \\}"'], 'puts "test \\{ and \\}"')

    def test_escaped_braces_in_code(self):
        """Test escaped braces in regular code."""
        tokens = list(TclReader.generate_tokens('set x \\{value\\}'))
        # Escaped braces should be treated as regular characters, not structural braces
        self.assertIn('\\{value\\}', ''.join(tokens))


class TestTclParser(unittest.TestCase):
    """Test TCL parsing and complexity calculation."""

    def test_empty_file(self):
        """Test empty TCL file."""
        functions = get_tcl_function_list("")
        self.assertEqual(0, len(functions))

    def test_no_function(self):
        """Test TCL code without procedures."""
        result = get_tcl_function_list('set x 10\nputs $x')
        self.assertEqual(0, len(result))

    def test_simple_proc(self):
        """Test simple procedure definition."""
        result = get_tcl_function_list('''
            proc hello {} {
                puts "Hello, World!"
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual("hello", result[0].name)
        self.assertEqual(0, result[0].parameter_count)
        self.assertEqual(1, result[0].cyclomatic_complexity)

    def test_proc_with_parameters(self):
        """Test procedure with parameters."""
        result = get_tcl_function_list('''
            proc add {a b} {
                return [expr {$a + $b}]
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual("add", result[0].name)
        self.assertEqual(2, result[0].parameter_count)

    def test_proc_with_default_params(self):
        """Test procedure with default parameter values."""
        result = get_tcl_function_list('''
            proc greet {name {greeting "Hello"}} {
                puts "$greeting, $name"
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual("greet", result[0].name)

    def test_multiple_procs(self):
        """Test multiple procedure definitions."""
        result = get_tcl_function_list('''
            proc func1 {} {
                puts "Function 1"
            }
            proc func2 {} {
                puts "Function 2"
            }
            proc func3 {} {
                puts "Function 3"
            }
        ''')
        self.assertEqual(3, len(result))
        self.assertEqual("func1", result[0].name)
        self.assertEqual("func2", result[1].name)
        self.assertEqual("func3", result[2].name)

    def test_if_statement(self):
        """Test if statement increases complexity."""
        result = get_tcl_function_list('''
            proc check {x} {
                if {$x > 5} {
                    puts "Greater than 5"
                }
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual(2, result[0].cyclomatic_complexity)

    def test_if_elseif_else(self):
        """Test if-elseif-else chain complexity."""
        result = get_tcl_function_list('''
            proc classify {x} {
                if {$x < 0} {
                    puts "Negative"
                } elseif {$x == 0} {
                    puts "Zero"
                } elseif {$x < 10} {
                    puts "Small positive"
                } else {
                    puts "Large positive"
                }
            }
        ''')
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (if) + 2 (elseif) = 4
        self.assertEqual(4, result[0].cyclomatic_complexity)

    def test_while_loop(self):
        """Test while loop increases complexity."""
        result = get_tcl_function_list('''
            proc countdown {n} {
                while {$n > 0} {
                    puts $n
                    incr n -1
                }
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual(2, result[0].cyclomatic_complexity)

    def test_for_loop(self):
        """Test for loop increases complexity."""
        result = get_tcl_function_list('''
            proc iterate {} {
                for {set i 0} {$i < 10} {incr i} {
                    puts $i
                }
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual(2, result[0].cyclomatic_complexity)

    def test_foreach_loop(self):
        """Test foreach loop increases complexity."""
        result = get_tcl_function_list('''
            proc print_list {items} {
                foreach item $items {
                    puts $item
                }
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual(2, result[0].cyclomatic_complexity)

    def test_switch_statement(self):
        """Test switch statement complexity (each pattern adds 1)."""
        result = get_tcl_function_list('''
            proc handle_command {cmd} {
                switch $cmd {
                    start {
                        puts "Starting"
                    }
                    stop {
                        puts "Stopping"
                    }
                    pause {
                        puts "Pausing"
                    }
                    default {
                        puts "Unknown command"
                    }
                }
            }
        ''')
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (switch) + 3 (patterns 2, 3, 4) = 5
        self.assertEqual(5, result[0].cyclomatic_complexity)

    def test_switch_simple_patterns(self):
        """Test simple switch with 3 patterns."""
        result = get_tcl_function_list('''
            proc test_switch {x} {
                switch $x {
                    1 { puts "One" }
                    2 { puts "Two" }
                    3 { puts "Three" }
                }
            }
        ''')
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (switch) + 2 (patterns 2 & 3) = 4
        self.assertEqual(4, result[0].cyclomatic_complexity)

    def test_switch_nested(self):
        """Test nested switch statements."""
        result = get_tcl_function_list('''
            proc test_nested {status level} {
                switch $status {
                    "unknown" {
                        set temp $level
                    }
                    "same" {
                        switch $level {
                            "unrelated" { set temp "a" }
                            "gated" { set temp "b" }
                            "ungated" { set temp "c" }
                        }
                    }
                    "other" {
                        switch $level {
                            "test" { set temp "x" }
                        }
                    }
                }
            }
        ''')
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (outer switch) + 2 (3 outer patterns)
        #      + 1 (inner switch 1) + 2 (3 inner patterns)
        #      + 1 (inner switch 2) + 0 (1 inner pattern)
        # = 1 + 1 + 2 + 1 + 2 + 1 + 0 = 8
        self.assertEqual(8, result[0].cyclomatic_complexity)

    def test_nested_control_flow(self):
        """Test nested control structures."""
        result = get_tcl_function_list('''
            proc process {x y} {
                if {$x > 0} {
                    while {$y > 0} {
                        if {$x == $y} {
                            puts "Equal"
                        }
                        incr y -1
                    }
                }
            }
        ''')
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (if) + 1 (while) + 1 (if) = 4
        self.assertEqual(4, result[0].cyclomatic_complexity)

    def test_logical_operators(self):
        """Test logical operators increase complexity."""
        result = get_tcl_function_list('''
            proc check_range {x y} {
                if {$x > 0 && $y > 0} {
                    puts "Both positive"
                }
                if {$x < 0 || $y < 0} {
                    puts "At least one negative"
                }
            }
        ''')
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (if) + 1 (&&) + 1 (if) + 1 (||) = 5
        self.assertEqual(5, result[0].cyclomatic_complexity)

    def test_catch_error_handling(self):
        """Test catch for error handling increases complexity."""
        result = get_tcl_function_list('''
            proc safe_divide {a b} {
                if {[catch {expr {$a / $b}} result]} {
                    puts "Error: $result"
                    return 0
                }
                return $result
            }
        ''')
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (if) = 2
        # Note: catch is part of the condition expression, not a separate decision point
        self.assertEqual(2, result[0].cyclomatic_complexity)

    def test_nloc_calculation(self):
        """Test NLOC (non-comment lines of code) calculation."""
        result = get_tcl_function_list('''
            proc example {} {
                # This is a comment
                set x 10
                
                # Another comment
                set y 20
                
                return [expr {$x + $y}]
            }
        ''')
        self.assertEqual(1, len(result))
        # Should count only non-comment, non-blank lines
        self.assertGreater(result[0].nloc, 0)

    def test_token_count(self):
        """Test token counting."""
        result = get_tcl_function_list('''
            proc add {a b} {
                return [expr {$a + $b}]
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertGreater(result[0].token_count, 0)

    def test_function_length(self):
        """Test function length calculation."""
        result = get_tcl_function_list('''
            proc multi_line {} {
                set x 1
                set y 2
                set z 3
                return $z
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertGreater(result[0].length, 4)

    def test_complex_real_world_example(self):
        """Test a more complex, realistic TCL procedure."""
        result = get_tcl_function_list('''
            proc process_data {data threshold} {
                set result [list]
                
                foreach item $data {
                    if {$item > $threshold} {
                        if {$item % 2 == 0} {
                            lappend result [expr {$item * 2}]
                        } elseif {$item % 3 == 0} {
                            lappend result [expr {$item * 3}]
                        } else {
                            lappend result $item
                        }
                    }
                }
                
                return $result
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual("process_data", result[0].name)
        self.assertEqual(2, result[0].parameter_count)
        # CC = 1 + 1(foreach) + 1(if) + 1(if) + 1(elseif) = 5
        # (else doesn't add to CC, only elseif does)
        self.assertEqual(5, result[0].cyclomatic_complexity)


class TestTclLanguageRecognition(unittest.TestCase):
    """Test that TCL files are recognized correctly."""

    def test_tcl_extension_recognition(self):
        """Test that .tcl extension is recognized."""
        from lizard_languages import get_reader_for
        self.assertEqual(TclReader, get_reader_for("script.tcl"))
        self.assertEqual(TclReader, get_reader_for("test.TCL"))

    def test_analyze_tcl_file(self):
        """Test analyzing a complete TCL file."""
        code = '''
            # TCL Script Example
            proc factorial {n} {
                if {$n <= 1} {
                    return 1
                } else {
                    return [expr {$n * [factorial [expr {$n - 1}]]}]
                }
            }
            
            proc main {} {
                for {set i 1} {$i <= 5} {incr i} {
                    puts "Factorial of $i is [factorial $i]"
                }
            }
        '''
        result = analyze_file.analyze_source_code("test.tcl", code)
        self.assertEqual(2, len(result.function_list))
        self.assertGreater(result.nloc, 0)


class TestTclNamespace(unittest.TestCase):
    """Test TCL namespace-qualified procedure names."""

    def test_namespace_qualified_proc(self):
        """Test procedure with namespace qualifier (::namespace::proc)."""
        result = get_tcl_function_list('''
            proc ::htree::create_routing_rules {args} {
                set tmpfile "test.txt"
                if {[file exists $tmpfile]} {
                    set score 10
                }
                return $score
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual("::htree::create_routing_rules", result[0].name)
        self.assertEqual(1, result[0].parameter_count)
        self.assertEqual(2, result[0].cyclomatic_complexity)

    def test_multiple_namespace_levels(self):
        """Test procedure with multiple namespace levels."""
        result = get_tcl_function_list('''
            proc ::company::product::module::function_name {x y} {
                if {$x > 0} {
                    return [expr {$x + $y}]
                }
                return 0
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual("::company::product::module::function_name", result[0].name)
        self.assertEqual(2, result[0].parameter_count)
        self.assertEqual(2, result[0].cyclomatic_complexity)

    def test_namespace_and_regular_procs_mixed(self):
        """Test mix of namespace-qualified and regular procedures."""
        result = get_tcl_function_list('''
            proc ::ns::func1 {} {
                puts "Namespaced"
            }
            
            proc regular_func {} {
                puts "Regular"
            }
            
            proc ::other::func2 {x} {
                if {$x > 0} {
                    return 1
                }
            }
        ''')
        self.assertEqual(3, len(result))
        self.assertEqual("::ns::func1", result[0].name)
        self.assertEqual("regular_func", result[1].name)
        self.assertEqual("::other::func2", result[2].name)
        self.assertEqual(2, result[2].cyclomatic_complexity)

    def test_namespace_with_default_params(self):
        """Test namespace-qualified proc with default parameters."""
        result = get_tcl_function_list('''
            proc ::utils::greet {name {greeting "Hello"}} {
                puts "$greeting, $name"
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual("::utils::greet", result[0].name)
        self.assertEqual(1, result[0].parameter_count)  # 'name' only, default value block is skipped


class TestTclRegsubBraceIssue(unittest.TestCase):
    """Test that regsub patterns with backslash-quote in braces don't break parsing."""

    def test_regsub_with_backslash_quote(self):
        """Test regsub with {\"} pattern."""
        result = get_tcl_function_list('''
            proc clean_string {str} {
                regsub {\"} $str "" result
                return $result
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual("clean_string", result[0].name)
        self.assertEqual(1, result[0].parameter_count)
        self.assertEqual(1, result[0].cyclomatic_complexity)

    def test_regsub_with_complex_pattern(self):
        """Test regsub with complex pattern {\"|\-}."""
        result = get_tcl_function_list('''
            proc clean_layers {text} {
                regsub {\"|\-} $text " " cleaned
                return $cleaned
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual("clean_layers", result[0].name)
        self.assertEqual(1, result[0].parameter_count)
        self.assertEqual(1, result[0].cyclomatic_complexity)

    def test_namespace_proc_with_regsub_backslash_quote(self):
        """Test namespace-qualified proc with regsub containing {\"|\-}."""
        result = get_tcl_function_list('''
            proc ::htree::create_routing_rules_get_layers { root layer_prefix } {
                global ivar
                set layers ""
                if {[info exists ivar(cts_htree,routing,layers,$root)] && $ivar(cts_htree,routing,layers,$root)!=""} {
                    regsub -all $layer_prefix $ivar(cts_htree,routing,layers,$root) "" tmp
                    regsub {\"|\-} $tmp " " layers
                } else {
                    regsub -all $layer_prefix $ivar(cts_htree,routing,layers,default) "" tmp
                    regsub {\"|\-} $tmp " " layers
                }
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual("::htree::create_routing_rules_get_layers", result[0].name)
        self.assertEqual(2, result[0].parameter_count)
        # CC = 1 (base) + 1 (if) + 1 (&&) = 3
        self.assertEqual(3, result[0].cyclomatic_complexity)

    def test_multiple_braced_patterns_in_proc(self):
        """Test procedure with multiple braced patterns containing special chars."""
        result = get_tcl_function_list('''
            proc process {text} {
                regsub {\\|} $text "_" step1
                regsub {\"} $step1 "'" step2
                regsub {\\-} $step2 "" result
                if {$result != ""} {
                    return $result
                }
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual("process", result[0].name)
        self.assertEqual(2, result[0].cyclomatic_complexity)


class TestTclCornerCases(unittest.TestCase):
    """Test corner cases and edge conditions in TCL parsing."""

    def test_deeply_nested_braces(self):
        """Test deeply nested braced content."""
        result = get_tcl_function_list('''
            proc nested_test {x} {
                if {$x > 0} {
                    set pattern {{{nested}}}
                    regsub $pattern $x "" result
                }
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual("nested_test", result[0].name)
        self.assertEqual(2, result[0].cyclomatic_complexity)

    def test_braces_with_mixed_quotes(self):
        """Test braces containing both single and double quotes."""
        result = get_tcl_function_list('''
            proc mixed_quotes {str} {
                regsub {"'} $str "" step1
                regsub {'"-} $step1 "" result
                return $result
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual("mixed_quotes", result[0].name)
        self.assertEqual(1, result[0].cyclomatic_complexity)

    def test_empty_braces_in_various_contexts(self):
        """Test empty braces {} in different contexts."""
        result = get_tcl_function_list('''
            proc empty_test {} {
                set dict [dict create]
                if {[llength $dict] == 0} {
                    return {}
                }
                return $dict
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual("empty_test", result[0].name)
        self.assertEqual(2, result[0].cyclomatic_complexity)

    def test_multiple_namespaces_in_file(self):
        """Test multiple namespace-qualified procs in one file."""
        result = get_tcl_function_list('''
            proc ::ns1::func1 {x} {
                if {$x > 0} { return 1 }
            }
            
            proc ::ns2::func2 {y} {
                while {$y > 0} { incr y -1 }
            }
            
            proc ::ns1::ns2::func3 {} {
                foreach item {1 2 3} { puts $item }
            }
        ''')
        self.assertEqual(3, len(result))
        self.assertEqual("::ns1::func1", result[0].name)
        self.assertEqual("::ns2::func2", result[1].name)
        self.assertEqual("::ns1::ns2::func3", result[2].name)
        self.assertEqual(2, result[0].cyclomatic_complexity)
        self.assertEqual(2, result[1].cyclomatic_complexity)
        self.assertEqual(2, result[2].cyclomatic_complexity)

    def test_complex_switch_with_default(self):
        """Test switch with default case and multiple patterns."""
        result = get_tcl_function_list('''
            proc handle_input {cmd} {
                switch -exact $cmd {
                    start { puts "Starting" }
                    stop { puts "Stopping" }
                    pause { puts "Pausing" }
                    resume { puts "Resuming" }
                    default { puts "Unknown: $cmd" }
                }
            }
        ''')
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (switch) + 4 (5 patterns - 1) = 6
        self.assertEqual(6, result[0].cyclomatic_complexity)

    def test_switch_with_glob_patterns(self):
        """Test switch with -glob option and wildcard patterns."""
        result = get_tcl_function_list('''
            proc match_pattern {str} {
                switch -glob $str {
                    a* { puts "Starts with a" }
                    *b { puts "Ends with b" }
                    *c* { puts "Contains c" }
                }
            }
        ''')
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (switch) + 2 (3 patterns - 1) = 4
        self.assertEqual(4, result[0].cyclomatic_complexity)

    def test_multiline_if_condition(self):
        """Test if with multiline condition using backslash continuation."""
        result = get_tcl_function_list('''
            proc check_complex {a b c} {
                if {$a > 0 && $b > 0 && $c > 0} {
                    return 1
                }
                return 0
            }
        ''')
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (if) + 2 (two &&) = 4
        self.assertEqual(4, result[0].cyclomatic_complexity)

    def test_nested_if_else(self):
        """Test deeply nested if-else structures."""
        result = get_tcl_function_list('''
            proc nested_conditions {x y} {
                if {$x > 0} {
                    if {$y > 0} {
                        if {$x > $y} {
                            return "x larger"
                        } else {
                            return "y larger or equal"
                        }
                    } else {
                        return "y not positive"
                    }
                } else {
                    return "x not positive"
                }
            }
        ''')
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 3 (three if statements) = 4
        self.assertEqual(4, result[0].cyclomatic_complexity)

    def test_proc_with_args_parameter(self):
        """Test proc with special 'args' parameter for variable arguments."""
        result = get_tcl_function_list('''
            proc variable_args {first args} {
                set count 0
                foreach arg $args {
                    incr count
                }
                return $count
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual("variable_args", result[0].name)
        self.assertEqual(2, result[0].parameter_count)
        self.assertEqual(2, result[0].cyclomatic_complexity)

    def test_catch_with_nested_commands(self):
        """Test catch with nested command substitution."""
        result = get_tcl_function_list('''
            proc safe_eval {expr} {
                if {[catch {expr $expr} result]} {
                    if {[catch {puts stderr $result}]} {
                        return "error"
                    }
                }
                return $result
            }
        ''')
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 2 (two if statements) = 3
        self.assertEqual(3, result[0].cyclomatic_complexity)

    def test_for_with_complex_initialization(self):
        """Test for loop with complex initialization and increment."""
        result = get_tcl_function_list('''
            proc loop_test {n} {
                for {set i 0; set j $n} {$i < $j} {incr i; incr j -1} {
                    if {$i == $j} {
                        break
                    }
                }
            }
        ''')
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (for) + 1 (if) = 3
        self.assertEqual(3, result[0].cyclomatic_complexity)

    def test_while_with_or_operator(self):
        """Test while loop with OR operator in condition."""
        result = get_tcl_function_list('''
            proc wait_condition {a b} {
                while {$a > 0 || $b > 0} {
                    if {$a > 0} {
                        incr a -1
                    } else {
                        incr b -1
                    }
                }
            }
        ''')
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (while) + 1 (||) + 1 (if) = 4
        self.assertEqual(4, result[0].cyclomatic_complexity)

    def test_foreach_with_multiple_lists(self):
        """Test foreach with multiple iteration variables."""
        result = get_tcl_function_list('''
            proc iterate_pairs {list1 list2} {
                foreach {a b} $list1 {c d} $list2 {
                    if {$a > $c} {
                        puts "$a > $c"
                    }
                }
            }
        ''')
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (foreach) + 1 (if) = 3
        self.assertEqual(3, result[0].cyclomatic_complexity)

    def test_regsub_all_with_complex_pattern(self):
        """Test regsub -all with complex regex pattern in braces."""
        result = get_tcl_function_list('''
            proc clean_all {text} {
                regsub -all {[\"'`]} $text "" cleaned
                regsub -all {\\s+} $cleaned " " final
                return $final
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual("clean_all", result[0].name)
        self.assertEqual(1, result[0].cyclomatic_complexity)

    def test_string_with_embedded_braces(self):
        """Test quoted strings containing brace characters."""
        result = get_tcl_function_list('''
            proc format_output {data} {
                set template "Result: {$data}"
                if {[string length $template] > 0} {
                    return $template
                }
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual(2, result[0].cyclomatic_complexity)

    def test_expr_with_ternary_like_structure(self):
        """Test expr with conditional expression."""
        result = get_tcl_function_list('''
            proc calculate {x y op} {
                if {$op eq "add"} {
                    set result [expr {$x + $y}]
                } elseif {$op eq "sub"} {
                    set result [expr {$x - $y}]
                } else {
                    set result 0
                }
                return $result
            }
        ''')
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (if) + 1 (elseif) = 3
        self.assertEqual(3, result[0].cyclomatic_complexity)

    def test_proc_with_upvar(self):
        """Test proc using upvar for variable reference."""
        result = get_tcl_function_list('''
            proc increment_var {varname} {
                upvar $varname var
                if {[info exists var]} {
                    incr var
                    return 1
                }
                return 0
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual(2, result[0].cyclomatic_complexity)

    def test_array_operations(self):
        """Test array operations with conditionals."""
        result = get_tcl_function_list('''
            proc array_check {arr_name key} {
                upvar $arr_name arr
                if {[info exists arr($key)]} {
                    if {$arr($key) > 0} {
                        return $arr($key)
                    }
                }
                return -1
            }
        ''')
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 2 (two if statements) = 3
        self.assertEqual(3, result[0].cyclomatic_complexity)

    def test_escaped_braces_in_proc(self):
        """Test proc with escaped braces in comments and strings."""
        result = get_tcl_function_list('''
            proc write_tcl_code {fp upf} {
                # This comment has escaped braces: \{ and \}
                # puts $fp "if \(\$derived\_upf\) \{"
                if {$upf == 1} {
                    puts $fp "test \\{ value \\}"
                }
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual("write_tcl_code", result[0].name)
        self.assertEqual(2, result[0].parameter_count)
        self.assertEqual(2, result[0].cyclomatic_complexity)

    def test_escaped_braces_comprehensive(self):
        """Test comprehensive handling of escaped braces (\\{ and \\}).
        
        This test covers the issue where escaped braces in comments or strings
        were being treated as structural braces, breaking the parser.
        
        Examples:
        - \\{ is an escaped opening brace (literal character, not structural)
        - \\\\{ is an escaped backslash followed by a real structural brace
        """
        result = get_tcl_function_list('''
            proc write_upf_code {fp derived_upf} {
                # Real-world comment that caused the original issue:
                # puts $fp "if \(\$derived\_upf\) \{"
                # The \\{ in the comment should NOT be treated as a structural brace
                
                if {$derived_upf} {
                    # Another comment with escaped braces: \\{ and \\}
                    puts $fp "test \\{ value \\}"
                    return 1
                }
                return 0
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual("write_upf_code", result[0].name)
        self.assertEqual(2, result[0].parameter_count)
        self.assertEqual(2, result[0].cyclomatic_complexity)

    def test_comments_with_special_chars(self):
        """Test that comments with special characters don't break parsing."""
        result = get_tcl_function_list('''
            proc test_comments {x} {
                # This comment has {braces} and "quotes"
                if {$x > 0} {
                    # Another comment with \\ backslashes
                    return 1
                }
                # Comment with || and && operators
                return 0
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual(2, result[0].cyclomatic_complexity)

    def test_command_substitution_in_condition(self):
        """Test command substitution within if condition."""
        result = get_tcl_function_list('''
            proc check_file {filename} {
                if {[file exists $filename] && [file readable $filename]} {
                    if {[file size $filename] > 0} {
                        return 1
                    }
                }
                return 0
            }
        ''')
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (if) + 1 (&&) + 1 (nested if) = 4
        self.assertEqual(4, result[0].cyclomatic_complexity)

    def test_variable_names_with_special_chars(self):
        """Test variable names with underscores and numbers."""
        result = get_tcl_function_list('''
            proc process_data {input_data_1 output_var_2} {
                set temp_123 $input_data_1
                if {$temp_123 > 0} {
                    set $output_var_2 $temp_123
                }
            }
        ''')
        self.assertEqual(1, len(result))
        self.assertEqual(2, result[0].parameter_count)
        self.assertEqual(2, result[0].cyclomatic_complexity)


class TestTclFlatCodeAnalysis(unittest.TestCase):
    """Test TCL flat code (code outside procs) complexity tracking."""

    def test_no_flat_code_complexity_without_extension(self):
        """Test that flat code is not counted without lizardoutside extension."""
        result = get_tcl_function_list('''
            set x 10
            if {$x > 5} {
                puts "Greater than 5"
            }
        ''')
        self.assertEqual(0, len(result))

    def test_flat_code_simple_if(self):
        """Test flat code with simple if statement."""
        result = get_tcl_function_list_with_extension('''
            set x 10
            if {$x > 5} {
                puts "Greater than 5"
            }
        ''', CountOutsideComplexity())
        self.assertEqual(1, len(result))
        self.assertEqual("*global*", result[0].name)
        # CC = 1 (base) + 1 (if) = 2
        self.assertEqual(2, result[0].cyclomatic_complexity)

    def test_flat_code_if_elseif(self):
        """Test flat code with if-elseif-else chain."""
        result = get_tcl_function_list_with_extension('''
            set x 10
            if {$x < 5} {
                puts "Less than 5"
            } elseif {$x < 10} {
                puts "Less than 10"
            } elseif {$x < 15} {
                puts "Less than 15"
            } else {
                puts "15 or more"
            }
        ''', CountOutsideComplexity())
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (if) + 2 (elseif) = 4
        self.assertEqual(4, result[0].cyclomatic_complexity)

    def test_flat_code_loops(self):
        """Test flat code with different loop types."""
        result = get_tcl_function_list_with_extension('''
            # For loop
            for {set i 0} {$i < 10} {incr i} {
                puts $i
            }
            
            # While loop
            set j 0
            while {$j < 5} {
                puts $j
                incr j
            }
            
            # Foreach loop
            foreach item {a b c} {
                puts $item
            }
        ''', CountOutsideComplexity())
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (for) + 1 (while) + 1 (foreach) = 4
        self.assertEqual(4, result[0].cyclomatic_complexity)

    def test_flat_code_logical_operators(self):
        """Test flat code with logical operators."""
        result = get_tcl_function_list_with_extension('''
            set x 10
            set y 20
            if {$x > 5 && $y < 30} {
                puts "Condition 1"
            }
            if {$x < 0 || $y > 100} {
                puts "Condition 2"
            }
        ''', CountOutsideComplexity())
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (if) + 1 (&&) + 1 (if) + 1 (||) = 5
        self.assertEqual(5, result[0].cyclomatic_complexity)

    def test_flat_code_nested_structures(self):
        """Test flat code with nested control structures."""
        result = get_tcl_function_list_with_extension('''
            set x 10
            if {$x > 0} {
                set y 5
                while {$y > 0} {
                    if {$x == $y} {
                        puts "Equal"
                    }
                    incr y -1
                }
            }
        ''', CountOutsideComplexity())
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (if) + 1 (while) + 1 (if) = 4
        self.assertEqual(4, result[0].cyclomatic_complexity)

    def test_flat_code_with_procs(self):
        """Test that flat code and procs are tracked separately."""
        result = get_tcl_function_list_with_extension('''
            # Flat code before proc
            if {1} {
                puts "Before"
            }
            
            proc my_proc {x} {
                if {$x > 0} {
                    return 1
                }
            }
            
            # Flat code after proc
            for {set i 0} {$i < 10} {incr i} {
                puts $i
            }
        ''', CountOutsideComplexity())
        self.assertEqual(2, len(result))
        
        # Find the proc
        proc = next(f for f in result if f.name == 'my_proc')
        self.assertEqual(2, proc.cyclomatic_complexity)  # 1 + 1 (if)
        
        # Find the global code
        global_func = next(f for f in result if f.name == '*global*')
        # CC = 1 (base) + 1 (if) + 1 (for) = 3
        self.assertEqual(3, global_func.cyclomatic_complexity)

    def test_flat_code_catch_error_handling(self):
        """Test flat code with catch for error handling."""
        result = get_tcl_function_list_with_extension('''
            set result 0
            if {[catch {expr {10 / 0}} error_msg]} {
                puts "Error: $error_msg"
            }
        ''', CountOutsideComplexity())
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (if) = 2
        # catch is part of the condition, not a separate decision point
        self.assertEqual(2, result[0].cyclomatic_complexity)

    def test_empty_flat_code(self):
        """Test that empty code still creates global function with CC=1."""
        result = get_tcl_function_list_with_extension('', CountOutsideComplexity())
        self.assertEqual(1, len(result))
        self.assertEqual("*global*", result[0].name)
        self.assertEqual(1, result[0].cyclomatic_complexity)

    def test_flat_code_only_comments(self):
        """Test flat code with only comments."""
        result = get_tcl_function_list_with_extension('''
            # This is a comment
            # Another comment
        ''', CountOutsideComplexity())
        self.assertEqual(1, len(result))
        self.assertEqual(1, result[0].cyclomatic_complexity)

    def test_complex_flat_code_realistic(self):
        """Test realistic complex flat code example."""
        result = get_tcl_function_list_with_extension('''
            set data {10 20 30 40}
            set threshold 15
            
            foreach item $data {
                if {$item > $threshold} {
                    if {$item % 2 == 0} {
                        puts "Even and above threshold: $item"
                    } elseif {$item % 3 == 0} {
                        puts "Divisible by 3: $item"
                    }
                }
            }
        ''', CountOutsideComplexity())
        self.assertEqual(1, len(result))
        # CC = 1 (base) + 1 (foreach) + 1 (if) + 1 (if) + 1 (elseif) = 5
        self.assertEqual(5, result[0].cyclomatic_complexity)


if __name__ == '__main__':
    unittest.main()
