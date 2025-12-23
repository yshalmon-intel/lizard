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
        
        Critical: TCL braces protect their content from interpretation. Content inside
        braces like {\"} should NOT trigger the quoted-string regex pattern.
        We solve this by masking all braced content before tokenization.
        """
        import re
        
        # Strategy: Recursively find and mask ALL braced content (handling nesting)
        # before standard tokenization, then restore after
        
        def mask_braces(text):
            """Recursively mask braced content with placeholders.
            
            Note: Escaped braces (\{ and \}) are NOT structural braces and should be ignored.
            However, if the backslash itself is escaped (\\{), then the brace IS structural.
            """
            masked = text
            replacements = {}
            counter = 0
            
            def is_escaped(text, pos):
                """Check if character at pos is escaped by counting preceding backslashes."""
                if pos == 0:
                    return False
                # Count consecutive backslashes before this position
                backslash_count = 0
                check_pos = pos - 1
                while check_pos >= 0 and text[check_pos] == '\\':
                    backslash_count += 1
                    check_pos -= 1
                # Odd number of backslashes means the character is escaped
                return backslash_count % 2 == 1
            
            # Keep processing until no more braced content found
            while True:
                found = False
                i = 0
                while i < len(masked):
                    if masked[i] == '{' and not is_escaped(masked, i):
                        # Found unescaped opening brace - find matching close
                        depth = 1
                        j = i + 1
                        while j < len(masked) and depth > 0:
                            if not is_escaped(masked, j):
                                if masked[j] == '{':
                                    depth += 1
                                elif masked[j] == '}':
                                    depth -= 1
                            j += 1
                        
                        if depth == 0:
                            # Found matching close brace
                            content = masked[i:j]  # Include braces
                            placeholder = f'__TCL_BRACE_{counter}__'
                            replacements[placeholder] = content
                            masked = masked[:i] + placeholder + masked[j:]
                            counter += 1
                            found = True
                            break  # Start over to handle nested cases
                    i += 1
                
                if not found:
                    break
            
            return masked, replacements
        
        def unmask_braces(token, replacements):
            """Recursively unmask braced content in a token."""
            if token in replacements:
                content = replacements[token]
                # Recursively unmask any nested placeholders in content
                for placeholder, original in replacements.items():
                    if placeholder in content:
                        content = content.replace(placeholder, original)
                return content
            return token
        
        def mask_quoted_strings(text):
            """Mask quoted strings that may contain nested brackets with quotes."""
            masked = text
            replacements = {}
            counter = 0
            i = 0
            
            while i < len(masked):
                if masked[i] == '"':
                    # Start of quoted string - find matching close quote
                    # Must handle nested brackets with their own quotes
                    j = i + 1
                    bracket_depth = 0
                    
                    while j < len(masked):
                        if masked[j] == '\\' and j + 1 < len(masked):
                            # Skip escaped character
                            j += 2
                            continue
                        elif masked[j] == '[':
                            bracket_depth += 1
                        elif masked[j] == ']':
                            bracket_depth -= 1
                        elif masked[j] == '"' and bracket_depth == 0:
                            # Found closing quote (not inside brackets)
                            break
                        j += 1
                    
                    if j < len(masked) and masked[j] == '"':
                        # Found complete quoted string
                        content = masked[i:j+1]  # Include quotes
                        placeholder = f'__TCL_STRING_{counter}__'
                        replacements[placeholder] = content
                        masked = masked[:i] + placeholder + masked[j+1:]
                        counter += 1
                        i += len(placeholder)
                        continue
                i += 1
            
            return masked, replacements
        
        # First mask all braced content (to protect quotes inside braces)
        masked_source, brace_replacements = mask_braces(source_code)
        
        # Then mask quoted strings (now protected from brace content)
        masked_source, string_replacements = mask_quoted_strings(masked_source)
        
        # Combine replacements
        replacements = {**brace_replacements, **string_replacements}
        
        # Tokenize the masked source (no braces or complex strings to confuse patterns)
        base_tokens = ScriptLanguageMixIn.generate_common_tokens(
            masked_source,
            # Match command substitution
            r"|\[[^\]]*\]" +
            # Match variable substitution
            r"|\$\w+" +
            addition,
            token_class)
        
        # Unmask tokens and expand braced content (but not strings)
        for token in base_tokens:
            # Check if this token is a string placeholder
            if token in string_replacements:
                # String placeholder - just yield the restored string as-is
                yield string_replacements[token]
            elif token in brace_replacements:
                # Brace placeholder - expand it
                original = brace_replacements[token]
                
                # Yield opening brace
                yield '{'
                
                # Recursively tokenize the inner content
                inner = original[1:-1]  # Remove outer braces
                if inner:
                    # Generate tokens for inner content
                    inner_tokens = TclReader.generate_tokens(inner, addition, token_class)
                    for inner_token in inner_tokens:
                        yield inner_token
                
                # Yield closing brace
                yield '}'
            else:
                # Regular token - restore any embedded placeholders and yield
                restored_token = token
                for placeholder, original in {**string_replacements, **brace_replacements}.items():
                    if placeholder in restored_token:
                        restored_token = restored_token.replace(placeholder, original)
                yield restored_token


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
        self.proc_name_parts = []  # For accumulating namespace-qualified names
        # Stack to track nested switches: each entry is (brace_level, pattern_count, return_state)
        self.switch_stack = []

    def _state_global(self, token):
        """Global state - looking for proc definitions and switch statements."""
        if token == 'proc':
            self.proc_name_parts = []  # Reset for new proc
            self.next(self._proc_name)
        elif token == 'switch':
            # Track switch for complexity - will add 1 for switch itself
            self.context.add_condition()
            self.next(self._switch_options)
        elif token == '}':
            # End of a block - might be end of function
            self.statemachine_return()

    def _proc_name(self, token):
        """Capture the procedure name, including namespace qualifiers (::)."""
        if token == '::':
            # Namespace separator - add to name parts
            self.proc_name_parts.append(token)
        elif token not in ['{', ' ', '\n', '\t']:
            # This is part of the proc name (namespace or actual name)
            self.proc_name_parts.append(token)
            # Check if next token might be :: or if we should expect parameters
            self.next(self._proc_name_continue)
        # Skip whitespace

    def _proc_name_continue(self, token):
        """Check if proc name continues with namespace qualifier or is complete."""
        if token == '::':
            # More namespace qualifiers coming
            self.proc_name_parts.append(token)
            self.next(self._proc_name)
        elif token == '{':
            # Name is complete, starting parameters
            self.proc_name = ''.join(self.proc_name_parts)
            self.context.push_new_function(self.proc_name)
            self.context.add_to_long_function_name("(")
            self.next(self._proc_params)
        elif token in [' ', '\n', '\t']:
            # Whitespace before parameters - name is complete
            self.proc_name = ''.join(self.proc_name_parts)
            self.context.push_new_function(self.proc_name)
            self.next(self._proc_params_start)
        else:
            # Error in syntax, return to global
            self.next(self._state_global)

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
        if token in ['-', '--']:
            # Dash for options or end-of-options marker - stay in this state
            pass
        elif token in ['exact', 'glob', 'regexp', 'nocase', 'indexed']:
            # These are option names that follow '-', just skip them
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
            # Check if this brace starts a pattern action block (at level 1)
            if current_switch['brace_level'] == 1:
                # At level 1, opening brace starts a pattern action block
                # Each pattern-action pair has the form: pattern { action }
                current_switch['pattern_count'] += 1
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
