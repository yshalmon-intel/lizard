'''
Language parser for TCL (Tool Command Language)
'''

from .code_reader import CodeReader, CodeStateMachine
from .script_language import ScriptLanguageMixIn


class TclReader(CodeReader, ScriptLanguageMixIn):
    """
    TCL language reader for Lizard code complexity analyzer.
    
    Supports:
    - proc definitions
    - Control flow: if/elseif/else, while, for, foreach, switch
    - Comments starting with #
    - Cyclomatic complexity calculation
    """

    ext = ['tcl']
    language_names = ['tcl']
    
    # Separated condition categories for cyclomatic complexity
    _control_flow_keywords = {'if', 'elseif', 'while', 'for', 'foreach'}
    _logical_operators = {'&&', '||', 'and', 'or'}
    _case_keywords = set()  # TCL switch patterns are tracked in state machine
    _ternary_operators = set()  # TCL uses if syntax, not ternary

    def __init__(self, context):
        super(TclReader, self).__init__(context)
        self.parallel_states = [TclStateMachine(context)]

    @staticmethod
    def generate_tokens(source_code, addition='', token_class=None):
        """
        Generate tokens for TCL source code.
        
        TCL-specific patterns:
        - Comments: # to end of line
        - Strings: "..." 
        - Command substitution: [...]
        - Variable substitution: $var
        - Braces: { and } are individual tokens
        """
        # TCL comment pattern: # followed by anything to end of line
        return ScriptLanguageMixIn.generate_common_tokens(
            source_code,
            # Match command substitution
            r"|\[[^\]]*\]" +
            # Match variable substitution
            r"|\$\w+" +
            addition,
            token_class)


class TclStateMachine(CodeStateMachine):
    """
    State machine for parsing TCL code structure.
    
    TCL syntax:
    - proc name {args} { body }
    - if {condition} { body }
    - while/for/foreach loops
    """

    def __init__(self, context):
        super(TclStateMachine, self).__init__(context)
        self.brace_count = 0
        self.proc_name = None
        # Stack to track nested switches: each entry is (brace_level, pattern_count, return_state)
        self.switch_stack = []

    def _state_global(self, token):
        """Global state - looking for proc definitions and switch statements."""
        if token == 'proc':
            self.next(self._proc_name)
        elif token == 'switch':
            # Track switch for complexity - will add 1 for switch itself
            self.context.add_condition()
            self.next(self._switch_options)
        elif token == '}':
            # End of a block - might be end of function
            self.statemachine_return()

    def _proc_name(self, token):
        """Capture the procedure name."""
        if token not in ['{', ' ', '\n', '\t']:
            # This is the proc name
            self.proc_name = token
            self.context.push_new_function(token)
            self.next(self._proc_params_start)
        # Skip whitespace

    def _proc_params_start(self, token):
        """Expecting opening brace for parameter list."""
        if token == '{':
            self.context.add_to_long_function_name("(")
            self.next(self._proc_params)
        elif token not in [' ', '\n', '\t']:
            # Error in syntax, return to global
            self.next(self._state_global)

    def _proc_params(self, token):
        """Parse parameter list inside braces."""
        if token == '}':
            self.context.add_to_long_function_name(")")
            self.next(self._proc_body_start)
        elif token == '{':
            # Start of a default value block - enter state to skip it
            self.next(self._proc_param_default)
        elif token not in [' ', '\n', '\t']:
            # Parameter name - TCL uses spaces instead of commas
            # Add a comma to separate parameters (except for the first one)
            if self.context.current_function.full_parameters:
                self.context.parameter(',')
            self.context.parameter(token)
    
    def _proc_param_default(self, token):
        """Skip default parameter value inside braces."""
        if token == '}':
            # End of default value, back to parameters
            self.next(self._proc_params)

    def _proc_body_start(self, token):
        """Expecting opening brace for procedure body."""
        if token == '{':
            self.brace_count = 1
            self.next(self._proc_body)
        elif token not in [' ', '\n', '\t']:
            # Error in syntax
            self.next(self._state_global)

    def _proc_body(self, token):
        """Inside procedure body - track braces and switch statements."""
        if token == 'switch':
            # Track switch for complexity
            self.context.add_condition()
            self.next(self._switch_options)
        elif token == '{':
            self.brace_count += 1
        elif token == '}':
            self.brace_count -= 1
            if self.brace_count == 0:
                # End of proc body
                self.context.end_of_function()
                self.next(self._state_global)

    def _switch_options(self, token):
        """After 'switch' keyword - may have options like -exact, -glob, -regexp, or the value directly."""
        if token in ['-exact', '-glob', '-regexp', '-nocase', '--']:
            # Skip switch options
            pass
        elif token == '{':
            # Start of switch body - push onto stack
            return_state = self._proc_body if self.brace_count > 0 else self._state_global
            self.switch_stack.append({'brace_level': 1, 'pattern_count': 0, 'return_state': return_state})
            self.next(self._switch_body)
        elif token not in [' ', '\n', '\t', '$']:
            # If not an option or brace, this is the variable/value being switched on
            # Next should be the opening brace of switch body
            self.next(self._switch_value)

    def _switch_value(self, token):
        """After the switch variable - expecting opening brace for switch body."""
        if token == '{':
            # Start of switch body - push onto stack
            return_state = self._proc_body if self.brace_count > 0 else self._state_global
            self.switch_stack.append({'brace_level': 1, 'pattern_count': 0, 'return_state': return_state})
            self.next(self._switch_body)
        elif token not in [' ', '\n', '\t']:
            # Error in syntax, return to previous state
            if self.brace_count > 0:
                self.next(self._proc_body)
            else:
                self.next(self._state_global)

    def _switch_body(self, token):
        """Inside switch body - count patterns (each pattern is a decision point)."""
        if len(self.switch_stack) == 0:
            # Error - no switch context, return to appropriate state
            if self.brace_count > 0:
                self.next(self._proc_body)
            else:
                self.next(self._state_global)
            return
        
        current_switch = self.switch_stack[-1]
        
        if token == 'switch':
            # Nested switch! Add complexity for this switch
            self.context.add_condition()
            self.next(self._switch_options)
        elif token == '{':
            current_switch['brace_level'] += 1
        elif token == '}':
            current_switch['brace_level'] -= 1
            if current_switch['brace_level'] == 0:
                # End of this switch body
                pattern_count = current_switch['pattern_count']
                return_state = current_switch['return_state']
                self.switch_stack.pop()
                
                # Add complexity for patterns (subtract 1 because switch itself already counted)
                if pattern_count > 0:
                    self.context.add_condition(pattern_count - 1)
                
                # If we're still in a switch (nested case), stay in switch_body
                if len(self.switch_stack) > 0:
                    self.next(self._switch_body)
                else:
                    self.next(return_state)
        elif current_switch['brace_level'] == 1 and token not in [' ', '\n', '\t', '#']:
            # At level 1 (inside switch body but outside pattern bodies), 
            # non-whitespace tokens are pattern names
            if not token.startswith('#'):  # Ignore comments
                current_switch['pattern_count'] += 1
