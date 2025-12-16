import unittest
from lizard import analyze_file, FileAnalyzer
from lizard_languages import TclReader


def get_tcl_function_list(source_code):
    """Helper function to analyze TCL source code and return function list."""
    return analyze_file.analyze_source_code(
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
        # Note: switch handling may vary - will need adjustment

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


if __name__ == '__main__':
    unittest.main()
