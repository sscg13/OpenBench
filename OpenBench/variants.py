# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#                                                                             #
#   OpenBench is a chess engine testing framework authored by Andrew Grant.   #
#   <https://github.com/AndyGrant/OpenBench>           <andrew@grantnet.us>   #
#                                                                             #
#   OpenBench is free software: you can redistribute it and/or modify         #
#   it under the terms of the GNU General Public License as published by      #
#   the Free Software Foundation, either version 3 of the License, or         #
#   (at your option) any later version.                                       #
#                                                                             #
#   OpenBench is distributed in the hope that it will be useful,              #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of            #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the             #
#   GNU General Public License for more details.                              #
#                                                                             #
#   You should have received a copy of the GNU General Public License         #
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.     #
#                                                                             #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

# Variant and Protocol vocabulary, shared by the Models, the import commands,
# the workload verification, and the management views.
#
# This module must not import Django, nor anything else from OpenBench, so that
# it can be used from OpenBench/models.py without any risk of a circular import.

VARIANT_TYPES = ('standard', 'fischerandom', 'shatranj')

VARIANT_LABELS = {
    'standard'     : 'Standard',
    'fischerandom' : 'Fischer Random',
    'shatranj'     : 'Shatranj',
}

DEFAULT_VARIANT = 'standard'

# Existing chess engines must keep playing both Standard and FRC books without
# needing to be re-imported. Shatranj is never implied: it must be declared.
DEFAULT_ENGINE_VARIANTS = ('standard', 'fischerandom')

PROTOCOL_TYPES = ('uci', 'xboard')

DEFAULT_PROTOCOL = 'uci'

SHATRANJ = 'shatranj'

# Ready-to-loop-over choices for the management Templates
VARIANT_CHOICES  = tuple((variant, VARIANT_LABELS[variant]) for variant in VARIANT_TYPES)
PROTOCOL_CHOICES = tuple((protocol, protocol.upper()) for protocol in PROTOCOL_TYPES)

def parse_variants(variants):

    # Accepts either a space separated string, as stored on the model, or any
    # iterable of names, as supplied by the import commands and their JSONs

    if isinstance(variants, str):
        return variants.split()

    return [str(variant) for variant in variants]

def join_variants(variants):
    return ' '.join(parse_variants(variants))

def verify_variant(variant):

    # Returns an error message, or None. Used for the single-valued Book.variant

    if variant not in VARIANT_TYPES:
        return 'Variant must be one of: %s' % (', '.join(VARIANT_TYPES))

    return None

def verify_variants(variants):

    # Returns an error message, or None. Used for EngineConfig.variants, which
    # is a non-empty, duplicate-free subset of VARIANT_TYPES

    variants = parse_variants(variants)

    if not variants:
        return 'Variants must list at least one of: %s' % (', '.join(VARIANT_TYPES))

    unknown = [variant for variant in variants if variant not in VARIANT_TYPES]
    if unknown:
        return 'Unknown variant(s): %s. Expected one of: %s' % (
            ', '.join(unknown), ', '.join(VARIANT_TYPES))

    if len(set(variants)) != len(variants):
        return 'Variants may not be listed more than once'

    return None

def verify_protocol(protocol):

    # Returns an error message, or None. Protocol is a property of the binary

    if protocol not in PROTOCOL_TYPES:
        return 'Protocol must be one of: %s' % (', '.join(PROTOCOL_TYPES))

    return None
