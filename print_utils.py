#!/usr/bin/python3

# Copyright (C) 2023 released Microchip Technology Inc.  All rights reserved.
# Microchip licenses to you the right to use, modify, copy and distribute
# Software only when embedded on a Microchip microcontroller or digital signal
# controller that is integrated into your product or third party product
# (pursuant to the sublicense terms in the accompanying license agreement).
# You should refer to the license agreement accompanying this Software for
# additional information regarding your rights and obligations.
# SOFTWARE AND DOCUMENTATION ARE PROVIDED AS IS WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION, ANY WARRANTY OF
# MERCHANTABILITY, TITLE, NON-INFRINGEMENT AND FITNESS FOR A PARTICULAR PURPOSE.
# IN NO EVENT SHALL MICROCHIP OR ITS LICENSORS BE LIABLE OR OBLIGATED UNDER
# CONTRACT, NEGLIGENCE, STRICT LIABILITY, CONTRIBUTION, BREACH OF WARRANTY, OR
# OTHER LEGAL EQUITABLE THEORY ANY DIRECT OR INDIRECT DAMAGES OR EXPENSES
# INCLUDING BUT NOT LIMITED TO ANY INCIDENTAL, SPECIAL, INDIRECT, PUNITIVE OR
# CONSEQUENTIAL DAMAGES, LOST PROFITS OR LOST DATA, COST OF PROCUREMENT OF
# SUBSTITUTE GOODS, TECHNOLOGY, SERVICES, OR ANY CLAIMS BY THIRD PARTIES
# (INCLUDING BUT NOT LIMITED TO ANY DEFENSE THEREOF), OR OTHER SIMILAR COSTS.

# @file     print_utils.py
#
# @brief    Various print function definitions
#
# @date     June 2, 2023
#
# @version  1.0.1
#
# @ref      http://www.linux-usb.org/usb.ids
#
# @brief    Displays a banner with upper and lower character bars with
#           the user message in between. Bar length is auto calculated
#           based on the banner_msg length. Each bar can be composed of
#           a single char or multiple characters i.e. '━' or '━◊━'
#           Use '\n' within the passed message to create a multi-line
#           banner. The leading space used on the first line of the
#           message is mirrored to the end of the string for single
#           and multiline banner messages.

#           Various banner line characters:
#           Note: Some chars are wider than standard text
#           ----------------------------------------------
#           * ⎯ ─ ━ ┉ ┈ ═ ═ = - _ [ ] ■ □ ▢ ▣ ▤ ▥ ▦ ▧ ▨ ▩
#           ▪ ▫ ▬ ▭ ▱ ▰ ▁ ▂ ▃ ▄ ▅ ▆ ▇ █ ╱ ╲ ◎ ◊ ◆ ◈ ◯
#           ▏ ▎ ▍ ▌ ▋ ▊ ▉ █
def max_line_len(msg: str) -> int:
  max_len = 0
  line1_space_len = len(msg) - len(msg.lstrip())
  if len(msg):
    not_line_one = 0

    for line in msg.splitlines():
      if not_line_one:
        line_x_space_len = len(line) - len(line.lstrip())
      else:
        line_x_space_len = 0
      white_space_add = (not_line_one * line1_space_len) + line1_space_len + line_x_space_len

      # A bit of a hack...If a non-line #1 is all white space, it gets added as if it was an
      # indent and makes the border lines really long. For now ignore all "white-space" lines
      # by limiting the indent to 4.
      if white_space_add > 4:
        white_space_add = line1_space_len
      if max_len < len(line) + white_space_add:
        max_len = len(line) + white_space_add
      not_line_one = 1
    return max_len


def banner(banner_msg: str, line_char: str = '─') -> None:
  """
  Prints a string message with a upper & lower character border
  Supports multi-line banners. If leading space is supplied on
  the first line, that space indents subsequent lines. Leading
  space is also mirrored to the end of the message lines.
  :param banner_msg: Required string to display
  :param line_char: [OPT] Single or multi-char border. [DEF] = '─'
  :return: Nothing
  """

  banner_len = max_line_len(banner_msg)
  lead_space = (len(banner_msg) - len(banner_msg.lstrip())) * ' '
  line_char_len = len(line_char)
  line = (line_char * int(banner_len / line_char_len) + line_char)[:banner_len]

  if banner_len:
    if line_char != '':
      print(f'{line}', flush=True)
    line_one = True
    for msg_line in banner_msg.splitlines():
      if line_one:
        print(f'{lead_space}{msg_line.lstrip()}', flush=True)
        line_one = False
      else:
        print(f'{lead_space}{msg_line}', flush=True)
    if line_char != '':
      print(f'{line}', flush=True)
          
def dbg_banner(msg: str, *args: any) -> None:
  """
  Override of a regular banner except it adds
  'DBG:' to the message and changes the default
  line character to '■'.
  """
  message = msg
  for num in args:
    message = message + ' ' + str(num)
  banner('DBG: ' + message, '■')


# Test
if __name__ == "__main__":
  border_list = ['*', '⎯', '─', '━', '┉', '┈', '═', '═',
                 '=', '-', '_', '[]', '■', '□', '▢', '▣',
                 '▤', '▥', '▦', '▧', '▨', '▩', '▪', '▫',
                 '▬', '▭', '▱', '▰', '╱ ╲', '◎', '◊', '◆',
                 '◈', '◯', '━◊━', 'v', 'w', 'x', 'X']
  print('\n' * 2, flush=True)
  hdr = f' col1      col2         col3           col4      col5          col6'
  dat = f"                                                                  "
  rsp = f'^^^^      ^^^^         ^^^^           ^^^^      ^^^^          ^^^^'
  print(f'{len(hdr)}, {len(hdr)}, {len(rsp)}', flush=True)
  banner(f'{hdr}\n{dat}\n{rsp}\n')
  banner(f'{hdr}\n{rsp}\n')

  exit(0)

  banner(" Default Banner\nMultiline\nBorder char NOT specified\n  Extra long indented Variable: 10\n  Status: Ok")
  print("\n", flush=True)
  banner("    Default Banner\nMultiline\nWith Mirrored\nLeading & Lagging\nWhite space\n  Variable: 10\n  Status: Ok")
  print("\n", flush=True)
  banner(" Default Banner - border char NOT specified")
  print("\n", flush=True)

  dbg_banner(" Ima\nMultiline\nDebug\nBanner")
  print("\n", flush=True)

  dbg_banner(" Ima Debug Banner")
  print("\n", flush=True)

  for type in border_list:
    banner(f'  Im-a-banner with "{type}" border\nIma longer second line as a test', type)
    print("\n", flush=True)