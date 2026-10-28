"""Library of saved study sets."""

import streamlit as st

from core import config, storage
from ui import theme
from ui.state import State


def render():
    theme.page_header(
        'Library',
        'Your saved study sets',
        'Everything you save stays local as JSON. Reopen a deck, export it, or clear space.',
    )
    entries = storage.list_study_sets()

    if not entries:
        theme.empty_state(
            '▦',
            'Your library is empty',
            'Generate a study set and press "Save to library" to keep it here.',
        )
        return

    total_cards = sum(entry['n_flashcards'] for entry in entries)
    total_questions = sum(entry['n_mcqs'] for entry in entries)
    total_attempts = sum(entry['n_attempts'] for entry in entries)
    theme.stat_snapshot(
        [
            ('Study sets', len(entries), 'Saved locally'),
            ('Flashcards', total_cards, 'Across all sets'),
            ('Questions', total_questions, 'Ready to practise'),
            ('Quiz attempts', total_attempts, 'Recorded in your sets'),
        ]
    )

    st.caption(f'{len(entries)} saved study set(s) in `{config.STUDY_SETS_DIR}`')

    table = [
        {
            'Topic': entry['topic'],
            'Subject': entry['subject'] or '-',
            'Created': entry['created_at'][:19].replace('T', ' '),
            'Cards': entry['n_flashcards'],
            'Questions': entry['n_mcqs'],
            'Attempts': entry['n_attempts'],
            'Engine': (entry.get('engine') or {}).get('model', '-'),
        }
        for entry in entries
    ]
    st.dataframe(table, width='stretch', hide_index=True)

    st.markdown('<div style="height:0.65rem"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        theme.section('01', 'Open or manage a saved set', 'Select a study set to continue where you left off.')
        labels = {entry['id']: f"{entry['topic']} - {entry['created_at'][:10]}" for entry in entries}
        selected_id = st.selectbox(
            'Study set',
            list(labels.keys()),
            format_func=lambda key: labels[key],
            key='library_select',
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button('Open', type='primary', width='stretch'):
                study_set = storage.load_study_set(selected_id)
                if study_set is None:
                    st.error('That study set could not be loaded.')
                else:
                    State.set_study_set(study_set)
                    State.set_warnings([])
                    State.set_current_view('Flashcards')
                    st.rerun()
        with c2:
            if st.button('Download JSON', width='stretch'):
                study_set = storage.load_study_set(selected_id)
                if study_set is None:
                    st.error('That study set could not be loaded.')
                else:
                    st.download_button(
                        'Save file',
                        data=storage.export_study_set(study_set),
                        file_name=f'{study_set.topic.replace(" ", "_")[:40]}.json',
                        mime='application/json',
                        key='library_download',
                    )
        with c3:
            if st.button('Delete', width='stretch'):
                if storage.delete_study_set(selected_id):
                    st.success('Study set deleted.')
                    st.rerun()
                else:
                    st.error('Nothing was deleted.')
